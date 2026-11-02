# Edit Video App – Backend (FastAPI)

Backend có hai nhóm API chạy chung một app:

- **API mobile** (`/auth`, `/me`, `/agents`, `/conversations`, `/search`, `/health`): backend tự quản lý tài khoản và JWT, dữ liệu trên Supabase PostgreSQL (project `editvideo-app`). Không dùng Supabase Auth, không xác thực số điện thoại.
- **API demo** (`/api/*`): đăng nhập bằng email, dữ liệu ở SQLite riêng.

## Cấu trúc thư mục

```text
backend/
├── app/
│   ├── main.py                    # Entry point FastAPI
│   ├── models.py                  # TOÀN BỘ bảng: 8 bảng Supabase + 4 bảng demo
│   ├── api/
│   │   ├── deps.py                # Dependencies của API demo
│   │   ├── supabase_deps.py       # Kiểm tra access token của app mobile
│   │   └── v1/
│   │       ├── router.py          # Tổng hợp API routes
│   │       └── endpoints/
│   │           ├── mobile_auth.py, me.py, agents.py, conversations.py, search.py     # API mobile
│   │           └── auth.py, users.py, dashboard.py, videos.py, schedule.py,
│   │               analytics.py, platforms.py, publishing.py                         # API demo
│   ├── core/                      # config.py, mobile_security.py (Argon2id, JWT), crypto.py (mã hóa key agent), security.py (API demo), logging.py, rate_limit.py, errors.py
│   ├── schemas/                   # mobile.py (API mobile); auth.py, user.py, content.py, schedule.py, integration.py
│   ├── services/                  # Business logic của API demo
│   ├── repositories/              # Truy vấn database của API demo
│   ├── db/
│   │   ├── supabase.py            # Kết nối Supabase (async), get_session
│   │   ├── session.py, base.py    # Kết nối database demo, get_db
│   │   ├── init_db.py             # Tạo bảng demo + dữ liệu demo
│   │   └── mock_data.py           # Dữ liệu demo trong RAM
│   ├── utils/helpers.py
│   └── integrations/              # goclaw.py, external_api.py
├── alembic/                       # Migration của database Supabase
├── tests/                         # Chạy bằng tests/run.sh
├── manage.py                      # Lệnh quản lý database
├── alembic.ini, pyproject.toml, uv.lock, requirements.txt, Dockerfile
└── .env / .env.example
```

## 1. Cài đặt (một lần)

Cần Python 3.12 trở lên và [uv](https://docs.astral.sh/uv/). Không dùng uv thì `python -m venv .venv`, kích hoạt rồi `pip install -r requirements.txt`.

```bash
cd backend
```

```bash
uv sync
```

Tạo file cấu hình (Windows: `copy .env.example .env`):

```bash
cp .env.example .env
```

Mở `backend/.env`, điền **DATABASE_URL**, **DB_PASSWORD** (mật khẩu database Supabase, quên thì vào
Dashboard → Project Settings → Database → **Reset database password**), **AUTH_JWT_SECRET** và **AGENT_KEY_ENCRYPTION_KEY**
(cách tạo ghi trong `.env.example`). Hai khóa này mỗi môi trường một bộ, không đưa lên git. Chỉ làm API demo thì có thể bỏ qua:
API mobile sẽ trả 503, API demo vẫn chạy.

```bash
uv run python manage.py migrate
```

Database Supabase của project đã ở phiên bản mới nhất nên lệnh này không làm gì. Trên database mới, lệnh dựng đủ 8 bảng. Rồi nạp agent mẫu và kiểm tra:

```bash
uv run python manage.py seed
```


```bash
uv run python manage.py check
```

phải in `Models và database khớp nhau.`

## 2. Tạo / sửa bảng bằng Python

Ví dụ thêm bảng `feedbacks` (user chấm điểm một cuộc trò chuyện):

**Bước 1** – thêm class vào cuối phần Supabase trong `app/models.py`, và thêm tên `"Feedback"` vào `__all__`:

```python
class Feedback(Base):
    __tablename__ = "feedbacks"
    __table_args__ = (
        # conversation phải thuộc đúng user này (giống các bảng khác)
        ForeignKeyConstraint(["conversation_id", "user_id"], ["conversations.id", "conversations.user_id"],
                             ondelete="CASCADE"),
        CheckConstraint("rating between 1 and 5", name="feedbacks_rating_chk"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)        # có "| None" = cho phép NULL
    created_at: Mapped[datetime] = created_at()
```

**Bước 2** – sinh file migration (so models với database thật):

```bash
uv run python manage.py make "them bang feedbacks"
```

Mở file mới trong `alembic/versions/` xem lại (bảng, cột, khóa ngoại). Bảng mới **tự được bật RLS**
và thu quyền của `anon`/`authenticated`, nên mobile không đọc trực tiếp được cho tới khi bạn thêm policy.

**Bước 3** – áp lên Supabase:

```bash
uv run python manage.py migrate
```

Vào Dashboard → Table Editor sẽ thấy bảng `feedbacks` với 2 khóa ngoại. Lỡ sai thì:

```bash
uv run python manage.py rollback
```

Sửa cột / thêm index / đổi kiểu cũng làm y như vậy: sửa class → `make` → `migrate`.

**Xóa bảng** thì khác: để an toàn, `make` không bao giờ tự sinh lệnh xóa bảng (kể cả bảng bạn tạo tay trên
Dashboard). Muốn xóa thật: bỏ class, rồi `make --empty "xoa bang abc"` và tự viết `op.drop_table("abc")`.

### Những thứ Alembic không tự sinh

Policy RLS, trigger, function, view, CHECK constraint **sửa sau khi đã tạo**: tạo migration trống rồi tự viết SQL.

```bash
uv run python manage.py make --empty "cho mobile doc feedbacks"
```

```python
def upgrade() -> None:
    op.execute("grant select on public.feedbacks to authenticated")
    op.execute("""create policy feedbacks_select_own on public.feedbacks for select to authenticated
                  using (user_id = (select auth.uid()))""")


def downgrade() -> None:
    op.execute("drop policy feedbacks_select_own on public.feedbacks")
    op.execute("revoke select on public.feedbacks from authenticated")
```

### Lệnh

| Lệnh | Làm gì |
|---|---|
| `manage.py make "mô tả"` | so models với database, sinh migration (không có thay đổi thì không sinh) |
| `manage.py make --empty "mô tả"` | migration trống để tự viết SQL |
| `manage.py migrate` | áp mọi migration chưa chạy |
| `manage.py rollback [n]` | hoàn tác n migration gần nhất (mặc định 1) |
| `manage.py status` | phiên bản hiện tại của database |
| `manage.py check` | models và database có khớp không |
| `manage.py seed` | nạp `supabase/seed.sql` (chạy lại nhiều lần an toàn) |
| `manage.py agent "Tên" --domain https://... --set-key` | tạo/sửa agent; API key nhập ẩn và được mã hóa trước khi lưu |
| `manage.py set-password 0912345678` | admin đặt lại mật khẩu (mọi token cũ của người đó hết tác dụng) |

Đặt `uv run python` trước mỗi lệnh, chạy trong thư mục `backend/`.

**Quy tắc:** chỉ đổi schema qua Python. Không sửa bảng bằng Table Editor của Supabase hay `supabase db push`,
nếu không `check` sẽ báo lệch.

## 3. Chạy API

```bash
uv run uvicorn app.main:app --reload --port 4000
```

Mở http://localhost:4000/docs để thử API. Các API mobile (trừ `/health` và đăng ký, đăng nhập) cần header
`Authorization: Bearer <access_token>` lấy từ `/auth/register` hoặc `/auth/login`.

| API | |
|---|---|
| `GET /health` | kiểm tra kết nối database |
| `POST /auth/register` | đăng ký, nhận token luôn |
| `POST /auth/login`, `/auth/refresh` | đăng nhập, gia hạn token |
| `POST /auth/change-password` | đổi mật khẩu, mọi token cũ hết tác dụng |
| `GET /me`, `PATCH /me`, `PATCH /me/settings` | hồ sơ, cài đặt |
| `GET /agents` | danh sách agent (chỉ id và tên, không trả key và domain) |
| `GET/POST /conversations` | danh sách (ghim trước, mới nhất trước) / tạo mới |
| `GET/PATCH/DELETE /conversations/{id}` | xem, đổi tên, ghim, lưu trữ, xóa mềm |
| `GET /conversations/{id}/messages?before=&limit=` | tin nhắn, mới nhất trước, phân trang theo `next_before` |
| `POST /conversations/{id}/messages` | gửi tin `{content, idempotency_key}`, chờ agent trả lời |
| `GET /search?q=` | tìm không dấu trong lịch sử chat |

Gửi tin: app tự sinh `idempotency_key` (UUID) cho mỗi lần bấm gửi. Mất mạng gửi lại cùng key thì
không tạo tin trùng. Mỗi cuộc trò chuyện chỉ một câu trả lời đang chạy; gửi chồng thì nhận `409`.
Mỗi user tối đa 20 tin/phút và 300 tin/giờ để không gọi AI vô hạn (`429`). Token, model, chi phí nằm trong `metadata` của tin.

### Đăng ký, đăng nhập và JWT

Backend tự quản lý: mật khẩu băm bằng Argon2id trong `users.password_hash`, JWT ký HS256 bằng `AUTH_JWT_SECRET`
(access token 30 phút, refresh token 30 ngày, đổi được qua `.env`). Mọi API kiểm tra chữ ký, hạn dùng, loại token,
và đọc lại tài khoản trong database, nên khóa tài khoản có hiệu lực ngay.

```text
Đăng ký:        POST /auth/register {phone, password, full_name}  -> access_token + refresh_token + user
Đăng nhập:      POST /auth/login    {phone, password}             -> access_token + refresh_token + user
Gọi API:        Authorization: Bearer <access_token>
Hết hạn (401):  POST /auth/refresh  {refresh_token}               -> cặp token mới, lưu đè cặp cũ
Đổi mật khẩu:   POST /auth/change-password {current_password, new_password} -> cặp token mới, lưu đè cặp cũ
Đăng xuất:      app tự xóa token trên máy (không có API)
```

Lưu ý khi làm app:

- Chỉ xóa token khi nhận `401` từ `/auth/refresh`. `503` và `429` là lỗi tạm thời: giữ token, thử lại sau.
- Lưu token trong SecureStore.
- Mặc định chỉ nhận số Việt Nam; `ALLOW_INTERNATIONAL_PHONES=true` để mở số nước ngoài.
- App chỉ đi qua API này. Mọi bảng đã khóa với anon key, không dùng được supabase-js hay Realtime để đọc dữ liệu.

Hệ quả của thiết kế hiện tại (không xác thực số điện thoại, không có bảng phiên):

- Ai cũng đăng ký được bằng số của người khác, và chủ số thật nhận `409`. Đăng ký cũng cho biết số nào đã có tài khoản.
- Không có Quên mật khẩu. Người dùng quên thì admin chạy `manage.py set-password`.
- Không thu hồi được từng token. Đăng xuất chỉ xóa token trên máy; token bị lộ dùng được tới khi hết hạn, và refresh token
  đổi được token mới liên tục. Cách cắt duy nhất: đổi mật khẩu hoặc khóa tài khoản (`users.status`).

Trước khi lên production:

1. Nếu chạy sau Nginx/load balancer: đặt biến môi trường `FORWARDED_ALLOW_IPS=<IP của proxy>` cho uvicorn, đừng dùng `*`.
   Thiếu thì mọi user chung một IP và đụng giới hạn của nhau (30 đăng ký/giờ, 100 đăng nhập/5 phút).
2. Giới hạn trong `app/core/rate_limit.py` đếm trong bộ nhớ: chạy nhiều worker thì chuyển sang Redis.
3. Tắt đăng ký của Supabase Auth trên Dashboard (Authentication → Sign In / Providers → Allow new users to sign up), vì app không dùng.

### GoClaw

`GOCLAW_MODE=mock` (mặc định) trả lời giả để làm app trước. Khi có GoClaw thật:

1. Đặt domain và API key cho từng agent (key nhập ẩn, được mã hóa bằng `AGENT_KEY_ENCRYPTION_KEY` trước khi lưu vào `agents.key`):

   ```bash
   uv run python manage.py agent "Trợ lý chung" --domain https://goclaw.cua-ban.com --set-key
   ```

2. Đặt `GOCLAW_MODE=openai`.

Client gọi `POST {agents.domain}/v1/chat/completions` với header `x-openclaw-session-key` = id cuộc trò chuyện. Đây là **giả định**
theo kiểu OpenClaw (chưa tìm được tài liệu API của GoClaw). Bảng `agents` không có id agent bên GoClaw nên mọi agent gọi cùng
`model = GOCLAW_DEFAULT_MODEL`; một domain chạy nhiều agent thì sẽ cần thêm cột. Kiểm tra với GoClaw thật rồi chỉnh
`_send_openai` trong `app/integrations/goclaw.py` nếu khác.

## 4. API demo `/api/*`

Các API này dùng cho màn hình web, đăng nhập bằng email và lưu ở database riêng (`LOCAL_DATABASE_URL`, mặc định SQLite
`connector_screen.db`). Tài khoản demo: `abc@gmail.com` / `123456`. Frontend đặt `VITE_API_BASE_URL=http://localhost:4000`.

- `GET /api/health`
- `POST /api/auth/register` · `POST /api/auth/login` · `POST /api/auth/google` · `POST /api/auth/forgot-password`
- `GET /api/users`
- `GET /api/dashboard`
- `POST /api/videos/generate`
- `GET /api/schedule` · `POST /api/schedule`
- `GET /api/analytics`
- `GET /api/platforms` · `GET /api/connectors` · `POST /api/connectors/{provider}`
- `POST /api/publishing`

Videos, analytics, publishing dùng dữ liệu demo trong RAM (`app/db/mock_data.py`), reset khi restart.
Token của `/api/auth/*` và token của `/auth/*` không dùng chung được.

Alembic chỉ quản lý database Supabase. Bảng demo được tạo tự động nhưng không tự thêm cột: sửa class demo trong `app/models.py` thì xóa `connector_screen.db` để tạo lại.

**Các API này chưa kiểm tra đăng nhập.** Khi lên production phải đặt `ENABLE_DEMO_API=false`.

## 5. Test

Test chạy trên một Postgres tạm trong bộ nhớ (PGlite, giả lập các schema của Supabase), **không** đụng tới Supabase thật.
Cần Node.js; lần đầu tự cài thư viện vào `tests/local_pg/`:

```bash
sh tests/run.sh
```

Chỉ chạy các test không cần Postgres (API demo, không cần Node.js):

```bash
uv run pytest
```

## 6. Chưa làm

- Xóa tài khoản `DELETE /me` (App Store yêu cầu với app có đăng ký). Tài khoản xóa mềm vẫn giữ số điện thoại vì `phone` là UNIQUE.
- Upload file đính kèm và ảnh đại diện: bucket Storage còn đó nhưng đã bỏ policy, cần API upload qua backend.
- Job xóa hẳn cuộc trò chuyện đã xóa mềm.
- Trả lời dạng streaming (hiện chờ trả lời xong mới trả về).
- Worker chạy `scheduled_tasks` trên VPS (mới có bảng, chưa có code).
