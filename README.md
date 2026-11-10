# Clipped-AI — AI-Powered Short-Form Video Generation SaaS

Clipped-AI allows users to upload authorized videos, describe what kind of short clip they want in natural language, and automatically generate engaging short-form vertical (9:16) videos with animated captions and an interactive video editor.

---

## 🚀 Key Features

- **Video Ingestion & FFprobe Extraction**: Validates formats and parses resolution, duration, codecs, bitrate, and audio streams.
- **Local Speech Transcription**: Transcribes speech using `faster-whisper` with word-level timestamps and VAD silence filtering on CPU with `int8` quantization.
- **Gemini Prompt Reasoning**: Extracts user intent, search keywords, tone, hook preferences, and duration constraints using structured JSON output from `gemini-3.8-flash`.
- **Deterministic Candidate Selection & Scoring**: Sliding window algorithm respecting sentence boundaries; multi-factor scoring (Hook strength, relevance, context flow, speech clarity) with optional Gemini re-ranking.
- **FFmpeg 9:16 Video Processing**: Trims accurate time segments, reframes to 9:16 vertical centre crop, generates stylized ASS/SRT subtitles with word highlights, and outputs clean MP4s.
- **Interactive In-Browser Video Editor**:
  - Live 9:16 canvas preview with play/pause, seek, and real-time styled caption overlays.
  - Multi-track timeline (video bar, caption blocks, playhead needle, split controls, zoom).
  - Caption styling (font family, font size, custom colors, alignment: top/center/bottom, animation presets).
  - Video visual effects (canvas zoom, pan offset, brightness, contrast, color filters: cinematic, vibrant, warm, cool, b&w).
  - Undo/redo history, reset to AI defaults, persistent backend storage, and direct MP4 export.
- **Production Architecture**:
  - FastAPI backend with Pydantic v2 schemas and async SQLAlchemy ORM.
  - SQLite for local dev, PostgreSQL/Supabase ready for production.
  - Alembic database migrations.
  - Celery background workers with Redis task queue for non-blocking asynchronous processing.
  - Next.js 15 App Router frontend with TypeScript and Tailwind CSS.

---

## 🛠 Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js 15 (App Router), TypeScript, Tailwind CSS, Lucide React |
| **Backend** | Python 3.14+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic |
| **AI Intelligence** | Google Gemini (`google-genai` SDK), `faster-whisper` (CTranslate2) |
| **Video Engine** | FFmpeg n9.0.2 with `libx264` and `libass` |
| **Task Queue** | Celery 5.7, Redis |
| **Database** | SQLite (`aiosqlite`) for dev, PostgreSQL (`asyncpg`) / Supabase ready |
| **Storage** | Local disk abstraction (`storage/` + `output/`) & Cloudflare R2 / S3 |

---

## 📦 Arch Linux Setup & Installation Guide

### 1. Prerequisites (System Packages)
Ensure system packages are up to date:
```bash
sudo pacman -Syu
sudo pacman -S python nodejs npm ffmpeg redis
```

### 2. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install greenlet email-validator autoprefixer

# Configure environment
cp .env.example .env
# Edit .env with your GEMINI_API_KEY if desired

# Run database migrations
alembic upgrade head

# Run unit and integration tests
pytest ../tests/ -v
```

### 3. Start Redis Server (for Celery background jobs)
```bash
# In a separate terminal or systemd:
redis-server
```

### 4. Start Celery Worker
```bash
cd backend
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info -Q video,ai
```

### 5. Start FastAPI Backend Server
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API docs will be accessible at: `http://localhost:8000/docs`

### 6. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Open your browser at: `http://localhost:3000`

---

## 📡 Backend API Reference (v1)

### Authentication
- `POST /api/v1/auth/register` — Register user account (returns JWT access & refresh tokens)
- `POST /api/v1/auth/login` — Sign in and receive bearer token
- `POST /api/v1/auth/refresh` — Refresh access token
- `GET /api/v1/auth/me` — Retrieve current authenticated profile

### Projects
- `POST /api/v1/projects` — Create project
- `GET /api/v1/projects` — List user projects (paginated)
- `GET /api/v1/projects/{project_id}` — Get project metadata
- `PATCH /api/v1/projects/{project_id}` — Update title, description, or status
- `DELETE /api/v1/projects/{project_id}` — Delete project and associated records

### Videos
- `POST /api/v1/videos/upload` — Ingest source video (multipart upload, triggers metadata extraction)
- `GET /api/v1/videos/{video_id}` — Video stream specifications and duration
- `GET /api/v1/videos/{video_id}/transcript` — Timestamped Whisper transcript segments

### Clips
- `POST /api/v1/clips/generate` — Trigger asynchronous AI clip generation job
- `GET /api/v1/clips?project_id={id}` — List candidate clips ranked by score
- `GET /api/v1/clips/{clip_id}` — Get clip details & score breakdown
- `PATCH /api/v1/clips/{clip_id}` — Select clip or modify properties
- `POST /api/v1/clips/{clip_id}/render` — Render MP4 vertical short
- `POST /api/v1/clips/{clip_id}/export` — Export final video with quality presets

### Video Editor
- `GET /api/v1/editor/{clip_id}` — Get or auto-initialize timeline data
- `PUT /api/v1/editor/{clip_id}` — Save timeline modifications and versioning
- `POST /api/v1/editor/{clip_id}/reset` — Reset timeline to original AI defaults

### Jobs & Health
- `GET /api/v1/jobs/{job_id}` — Poll background job progress and status
- `DELETE /api/v1/jobs/{job_id}/cancel` — Revoke Celery task
- `GET /api/v1/health` — API health status & uptime
- `GET /api/v1/ready` — Database and system readiness probe
- `GET /api/v1/info` — Application capabilities and models

---

## 🧪 Testing

Run backend tests:
```bash
pytest tests/ -v
```
Tests cover:
- Health & Info endpoints
- Authentication registration, password verification, and token exchange
- Project lifecycle and database integrity
- Heuristic and Gemini prompt intent parser
- Transcript sliding window candidate generation
- Multi-factor deterministic clip scoring
- Subtitle (.srt / .ass) file generation
- Timeline editor data schema and versioning

---

## 🔒 Security & Privacy

- **Authorized Media Only**: Only user-uploaded media files are accepted.
- **Data Isolation**: All database queries strictly scope projects and clips to the authenticated user ID (`user_id`).
- **Safe Subprocess Execution**: All FFmpeg and FFprobe calls execute using explicit argument lists (no shell injection vulnerabilities).
- **Password Security**: Direct `bcrypt` key derivation with automated 72-byte safe bounds.
- **Resource Cleanup**: Automated directory cleanup for intermediate audio and video rendering artifacts.
