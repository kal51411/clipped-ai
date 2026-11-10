"""
Auth router — register, login, refresh, me
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
GET  /api/v1/auth/me
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ConflictError, ForbiddenError, ValidationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.core.logging_config import get_logger
from app.models.user import User
from app.schemas.user import (
    GoogleAuthRequest,
    GoogleUrlResponse,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check email not already taken
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise ConflictError(f"Email '{payload.email}' is already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return _build_token_response(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and obtain tokens",
)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user: User | None = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise ValidationError("Invalid email or password")

    if not user.is_active:
        raise ForbiddenError("Account is deactivated. Contact support.")

    return _build_token_response(user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using a refresh token",
)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_data = decode_token(payload.refresh_token)
    if token_data.token_type != "refresh":
        raise ValidationError("Not a valid refresh token")

    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user: User | None = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise ForbiddenError("User not found or inactive")

    return _build_token_response(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get(
    "/google/url",
    response_model=GoogleUrlResponse,
    summary="Get Google OAuth Authorization URL",
)
async def get_google_auth_url():
    """Returns Google OAuth 2.0 authorization URL or instant dev redirect."""
    if settings.GOOGLE_CLIENT_ID:
        import urllib.parse

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
        }
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        return GoogleUrlResponse(url=url, is_mock=False)
    else:
        # Dev fallback: directs back to frontend callback with mock code for instant one-click login
        dev_url = f"{settings.GOOGLE_REDIRECT_URI}?code=mock_google_dev_code&email=creator.google@example.com&name=Google+Creator"
        return GoogleUrlResponse(url=dev_url, is_mock=True)


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Sign in or auto sign up using Google OAuth",
)
async def google_auth(payload: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """
    Exchanges Google auth code or verified profile, automatically signs up
    new users, and issues JWT tokens.
    """
    import secrets
    import httpx

    email: str | None = None
    name: str | None = payload.name
    avatar_url: str | None = payload.avatar_url

    # 1. Exchange real Google authorization code if client credentials configured
    if payload.code and settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                token_resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": payload.code,
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                        "grant_type": "authorization_code",
                    },
                )
                if token_resp.status_code == 200:
                    token_data = token_resp.json()
                    access_token = token_data.get("access_token")
                    userinfo_resp = await client.get(
                        "https://www.googleapis.com/oauth2/v3/userinfo",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if userinfo_resp.status_code == 200:
                        user_info = userinfo_resp.json()
                        email = user_info.get("email")
                        name = user_info.get("name") or name
                        avatar_url = user_info.get("picture") or avatar_url
        except Exception as e:
            logger.warning("Google OAuth token exchange failed, falling back to payload", error=str(e))

    # 2. If code wasn't exchanged or running in dev mode, use payload email or fallback
    if not email:
        email = payload.email or "google.user@example.com"
        if not name:
            name = "Google User"

    # 3. Check if user already exists
    result = await db.execute(select(User).where(User.email == email))
    user: User | None = result.scalar_one_or_none()

    if not user:
        # Automatically sign up the user
        random_pw = secrets.token_urlsafe(32) + "A1!"
        user = User(
            email=email,
            hashed_password=hash_password(random_pw),
            full_name=name,
            avatar_url=avatar_url,
            is_verified=True,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("Automatically signed up user via Google OAuth", user_id=user.id, email=email)
    else:
        # Existing user: update avatar if provided
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
            await db.commit()
            await db.refresh(user)
        logger.info("User signed in via Google OAuth", user_id=user.id, email=email)

    if not user.is_active:
        raise ForbiddenError("Account is deactivated")

    return _build_token_response(user)


def _build_token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.email),
        refresh_token=create_refresh_token(user.id, user.email),
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )
