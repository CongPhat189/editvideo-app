from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.auth import ForgotPasswordRequest, GoogleLoginRequest, LoginRequest, RegisterRequest
from app.services.auth_service import login_google_user, login_user, register_user, send_reset_password

router = APIRouter(prefix="/api/auth", tags=["auth"])



@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    if not payload.email:
        raise HTTPException(status_code=400, detail={"message": "Email là bắt buộc."})
    try:
        return register_user(db, payload.full_name or "User", payload.email, payload.password or "", payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={"message": str(exc)}) from exc


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    email = (payload.email or "").strip().lower()
    password = (payload.password or "").strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail={"message": "Email và mật khẩu là bắt buộc."})

    try:
        return login_user(db, email, password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={"message": str(exc)}) from exc


@router.post("/google")
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)) -> dict:
    email = (payload.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail={"message": "Thiếu thông tin Google."})

    return login_google_user(db, email, payload.name)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest) -> dict:
    email = (payload.email or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail={"message": "Email là bắt buộc."})

    return send_reset_password(email)
