import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app import supabase_auth
from app.auth import Session, verified_token
from app.models import Profile
from app.schemas import (
    AuthUser,
    LoginIn,
    OtpOut,
    RefreshIn,
    RegisterIn,
    RegisterOut,
    ResendOtpIn,
    TokenOut,
    VerifyOtpIn,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _http_error(e: supabase_auth.AuthError) -> HTTPException:
    return HTTPException(e.status_code, e.message)


async def _token_out(session: Session, auth: supabase_auth.AuthSession, client_ip: str | None) -> TokenOut:
    """Ghép token với hồ sơ. Tài khoản bị khóa thì thu hồi phiên vừa cấp và không trả token."""
    profile = await session.get(Profile, uuid.UUID(auth.user_id))
    full_name, account_status = (profile.full_name, profile.status) if profile else (None, None)
    await session.rollback()  # không giữ kết nối DB khi gọi Supabase Auth
    if account_status != "active":
        try:
            await supabase_auth.logout(auth.access_token, client_ip=client_ip)
        except supabase_auth.AuthError:
            pass  # lỗi này không đổi kết quả: vẫn không trả token
        if profile is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Hồ sơ chưa sẵn sàng, vui lòng thử lại")
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản đã bị khóa")
    phone = f"+{auth.phone.removeprefix('+')}" if auth.phone else None
    return TokenOut(
        access_token=auth.access_token,
        refresh_token=auth.refresh_token,
        token_type=auth.token_type,
        expires_in=auth.expires_in,
        expires_at=auth.expires_at,
        user=AuthUser(id=auth.user_id, phone=phone, full_name=full_name),
    )


@router.post("/register", response_model=RegisterOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, request: Request, session: Session):
    """Đăng ký bằng số điện thoại + mật khẩu. Thường cần bước /auth/verify-otp để nhận token."""
    ip = _client_ip(request)
    try:
        auth = await supabase_auth.sign_up(body.phone, body.password, body.full_name, client_ip=ip)
    except supabase_auth.AuthError as e:
        raise _http_error(e)
    if auth is None:
        return RegisterOut(phone=body.phone, otp_required=True)
    return RegisterOut(phone=body.phone, otp_required=False, session=await _token_out(session, auth, ip))


@router.post("/verify-otp", response_model=TokenOut)
async def verify_otp(body: VerifyOtpIn, request: Request, session: Session):
    """Xác minh mã SMS, thành công thì trả token."""
    ip = _client_ip(request)
    try:
        auth = await supabase_auth.verify_otp(body.phone, body.otp, client_ip=ip)
    except supabase_auth.AuthError as e:
        raise _http_error(e)
    return await _token_out(session, auth, ip)


@router.post("/resend-otp", response_model=OtpOut, status_code=status.HTTP_202_ACCEPTED)
async def resend_otp(body: ResendOtpIn, request: Request):
    try:
        await supabase_auth.resend_otp(body.phone, client_ip=_client_ip(request))
    except supabase_auth.AuthError as e:
        raise _http_error(e)
    return OtpOut(phone=body.phone)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, session: Session):
    ip = _client_ip(request)
    try:
        auth = await supabase_auth.login(body.phone, body.password, client_ip=ip)
    except supabase_auth.AuthError as e:
        raise _http_error(e)
    return await _token_out(session, auth, ip)


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, request: Request, session: Session):
    """Đổi refresh token lấy cặp token mới. Refresh token cũ hết dùng được: app phải lưu lại token mới."""
    ip = _client_ip(request)
    try:
        auth = await supabase_auth.refresh(body.refresh_token, client_ip=ip)
    except supabase_auth.AuthError as e:
        raise _http_error(e)
    return await _token_out(session, auth, ip)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token: Annotated[str, Depends(verified_token)],
    request: Request,
    all_devices: Annotated[bool, Query(description="true: đăng xuất khỏi mọi thiết bị")] = False,
):
    try:
        await supabase_auth.logout(token, all_devices=all_devices, client_ip=_client_ip(request))
    except supabase_auth.AuthError as e:
        raise _http_error(e)
