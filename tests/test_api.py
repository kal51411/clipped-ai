"""
Unit & Integration Tests for Clipped-AI Backend
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import sys
import os

# Add backend to path
sys.path.insert(0, "/home/kalpesh/clipped-ai/backend")

from app.main import app
from app.core.config import settings
from app.core.database import engine, Base


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["success"] is True


@pytest.mark.asyncio
async def test_app_info():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/info")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Clipped-AI"
        assert "features" in data


@pytest.mark.asyncio
async def test_auth_and_project_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register
        email = f"user_{os.urandom(4).hex()}@example.com"
        reg_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecurePassword123!",
                "full_name": "Test Creator",
            },
        )
        assert reg_resp.status_code == 201, reg_resp.text
        tokens = reg_resp.json()
        assert "access_token" in tokens
        token = tokens["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get profile
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == email

        # 3. Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "title": "Podcast Episode 12",
                "description": "Discussion on AI and jobs",
            },
        )
        assert proj_resp.status_code == 201
        project = proj_resp.json()
        assert project["title"] == "Podcast Episode 12"
        project_id = project["id"]

        # 4. List projects
        list_resp = await client.get("/api/v1/projects", headers=headers)
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        assert any(p["id"] == project_id for p in items)

        # 5. Create a mock clip directly in DB or via schema to test Editor endpoints
        from app.models.clip import Clip
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            clip = Clip(
                project_id=project_id,
                start_time=10.0,
                end_time=40.0,
                duration=30.0,
                transcript_text="Test clip text",
                segments=[{"start": 10.0, "end": 20.0, "text": "Hello world", "words": []}],
                score=0.95,
                rank=1,
                status="candidate",
            )
            db.add(clip)
            await db.commit()
            await db.refresh(clip)
            clip_id = clip.id

        # 6. Test Editor GET (auto-initializes default timeline)
        editor_resp = await client.get(f"/api/v1/editor/{clip_id}", headers=headers)
        assert editor_resp.status_code == 200, editor_resp.text
        ed_data = editor_resp.json()
        assert ed_data["clip_id"] == clip_id
        assert ed_data["timeline_data"]["total_duration"] == 30.0
        assert len(ed_data["timeline_data"]["captions"]) == 1

        # 7. Test Editor PUT (updates timeline)
        tl = ed_data["timeline_data"]
        tl["aspect_ratio"] = "9:16"
        tl["captions"][0]["font_size"] = 36
        update_resp = await client.put(
            f"/api/v1/editor/{clip_id}",
            headers=headers,
            json={"timeline_data": tl},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["version"] == 2
        assert update_resp.json()["timeline_data"]["captions"][0]["font_size"] == 36


@pytest.mark.asyncio
async def test_google_oauth_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test Google Auth URL
        url_resp = await client.get("/api/v1/auth/google/url")
        assert url_resp.status_code == 200
        data = url_resp.json()
        assert "url" in data

        # 2. Test Google OAuth auto sign-up and sign-in
        google_email = f"google_user_{os.urandom(4).hex()}@example.com"
        auth_resp = await client.post(
            "/api/v1/auth/google",
            json={
                "email": google_email,
                "name": "Alex Google Creator",
                "avatar_url": "https://lh3.googleusercontent.com/a/default-avatar",
            },
        )
        assert auth_resp.status_code == 200, auth_resp.text
        tokens = auth_resp.json()
        assert "access_token" in tokens
        assert tokens["user"]["email"] == google_email
        assert tokens["user"]["full_name"] == "Alex Google Creator"
        assert tokens["user"]["is_verified"] is True


@pytest.mark.asyncio
async def test_youtube_import_and_quick_shorts(monkeypatch):
    # Mock download_video_from_url so test does not require live YouTube network fetch
    def mock_download(url, output_path):
        import os
        from pathlib import Path
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(b"\x00" * 1024)
        return {
            "title": "Lex Fridman Podcast #400 - AI Future",
            "duration": 3600,
            "extractor": "youtube",
            "uploader": "Lex Fridman",
            "file_size_bytes": 1024,
            "file_path": output_path,
        }

    def mock_metadata(url):
        return {
            "title": "Lex Fridman Podcast #400 - AI Future",
            "duration": 3600,
            "extractor": "youtube",
            "uploader": "Lex Fridman",
        }

    from app.video.ingestion import url_downloader
    monkeypatch.setattr(url_downloader, "download_video_from_url", mock_download)
    monkeypatch.setattr(url_downloader, "extract_url_metadata", mock_metadata)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register & get auth token
        email = f"yt_user_{os.urandom(4).hex()}@example.com"
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Password123!", "full_name": "YT Shorts Creator"},
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create project & test video import-url
        proj = await client.post("/api/v1/projects", headers=headers, json={"title": "Podcast Test"})
        assert proj.status_code == 201
        project_id = proj.json()["id"]

        import_resp = await client.post(
            "/api/v1/videos/import-url",
            headers=headers,
            json={"project_id": project_id, "url": "https://www.youtube.com/watch?v=mock123"},
        )
        assert import_resp.status_code == 201, import_resp.text
        vdata = import_resp.json()
        assert "Lex Fridman Podcast" in vdata["original_filename"]
        assert vdata["storage_backend"] == "local"

        # 3. Test One-Click Quick YouTube to Shorts
        quick_resp = await client.post(
            "/api/v1/projects/quick-youtube",
            headers=headers,
            json={
                "url": "https://www.youtube.com/watch?v=mock456",
                "prompt": "Extract the most mind-blowing AI moment",
                "target_duration_seconds": 30,
            },
        )
        assert quick_resp.status_code == 201, quick_resp.text
        qdata = quick_resp.json()
        assert "project" in qdata
        assert "video_id" in qdata
        assert "job_id" in qdata
        assert qdata["project"]["title"] == "Lex Fridman Podcast #400 - AI Future"

