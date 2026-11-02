import uuid

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.api.supabase_deps import CurrentUser, Session, load_token_user
from app.core.errors import pg_error
from app.core.mobile_security import burn_verify_time, hash_password, issue_tokens, verify_password
from app.core.rate_limit import limiter
from app.models import AppUser, UserSetting
from app.schemas.mobile import AuthUser, ChangePasswordIn, LoginIn, RefreshIn, RegisterIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])

BAD_LOGIN = "Sai số điện thoại hoặc mật khẩu"


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _token_out(user_id, password_hash: str, phone: str, full_name: str) -> TokenOut:
    tokens = issue_tokens(user_id, password_hash)
    return TokenOut(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        expires_at=tokens.expires_at,
        user=AuthUser(id=user_id, phone=phone, full_name=full_name),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, request: Request, session: Session):
    """Đăng ký bằng số điện thoại + mật khẩu, nhận token luôn (không xác thực số điện thoại)."""
    limiter.hit(f"register:ip:{_client_ip(request)}", 30, 3600)
    password_hash = await run_in_threadpool(hash_password, body.password)
    user = AppUser(id=uuid.uuid4(), full_name=body.full_name, phone=body.phone, password_hash=password_hash)
    # Tạo token trước khi commit: thiếu cấu hình thì không để lại tài khoản không đăng nhập được
    tokens = _token_out(user.id, password_hash, body.phone, body.full_name)
    session.add(user)
    try:
        await session.flush()
        session.add(UserSetting(user_id=user.id))
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        if pg_error(e)[1] == "users_phone_key":
            raise HTTPException(status.HTTP_409_CONFLICT, "Số điện thoại này đã được đăng ký")
        raise
    return tokens


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, session: Session):
    ip = _client_ip(request)
    phone_failures = f"login:phone-failed:{body.phone}"
    limiter.hit(f"login:ip:{ip}", 100, 300)
    limiter.hit(f"login:ip-phone:{ip}:{body.phone}", 10, 300)
    # Chặn dò mật khẩu một số từ nhiều IP. Chỉ đếm lần sai và để ngưỡng cao, để kẻ gian khó khóa chủ tài khoản.
    limiter.check(phone_failures, 50, 900)

    user = await session.scalar(select(AppUser).where(AppUser.phone == body.phone))
    found = None if user is None else (user.id, user.password_hash, user.full_name, user.status)
    await session.rollback()  # không giữ kết nối DB khi băm mật khẩu
    if found is None:
        await run_in_threadpool(burn_verify_time, body.password)
        limiter.record(phone_failures)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, BAD_LOGIN)
    user_id, password_hash, full_name, account_status = found
    if not await run_in_threadpool(verify_password, body.password, password_hash) or account_status == "deleted":
        limiter.record(phone_failures)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, BAD_LOGIN)
    if account_status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản đã bị khóa")

    tokens = _token_out(user_id, password_hash, body.phone, full_name)
    await session.execute(update(AppUser).where(AppUser.id == user_id).values(last_login_at=func.now()))
    await session.commit()
    return tokens


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, request: Request, session: Session):
    """Đổi refresh token lấy cặp token mới. 401 nghĩa là phải đăng nhập lại."""
    limiter.hit(f"refresh:ip:{_client_ip(request)}", 60, 300)
    user = await load_token_user(session, body.refresh_token, "refresh")
    return _token_out(user.id, user.password_hash, user.phone, user.full_name)


@router.post("/change-password", response_model=TokenOut)
async def change_password(body: ChangePasswordIn, user: CurrentUser, session: Session):
    """Đổi mật khẩu. Mọi token cũ trên mọi thiết bị hết tác dụng, app phải lưu cặp token mới trả về."""
    limiter.hit(f"change-password:{user.id}", 10, 300)
    user_id, phone, full_name, current_hash = user.id, user.phone, user.full_name, user.password_hash
    await session.rollback()
    if not await run_in_threadpool(verify_password, body.current_password, current_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mật khẩu hiện tại không đúng")
    new_hash = await run_in_threadpool(hash_password, body.new_password)
    tokens = _token_out(user_id, new_hash, phone, full_name)
    await session.execute(update(AppUser).where(AppUser.id == user_id).values(password_hash=new_hash))
    await session.commit()
    return tokens
