# Backend FastAPI – GoClaw Mobile

FastAPI + SQLAlchemy 2 + Alembic, kết nối Supabase PostgreSQL (project `editvideo-app`).

```text
backend/
  app/
    models/          # 16 bảng viết bằng Python (khớp 100% database trên Supabase)
      users.py       #   profiles, user_settings, devices, notifications, notification_deliveries
      agents.py      #   goclaw_workspaces, agents, user_agent_access
      chat.py        #   conversations, messages, message_attachments
      tasks.py       #   social_accounts, scheduled_tasks, scheduled_task_runs, scheduled_task_logs, outbox_events
    routers/         # API: me, agents, conversations (+ chat), search
    auth.py          # kiểm tra access token Supabase (JWKS)
    goclaw.py        # gọi GoClaw (mock / OpenAI-compatible)
    config.py, db.py, schemas.py, main.py
  migrations/        # Alembic: 0001_baseline, ..._chi_nhan_timezone_iana, + các migration sau này
  manage.py          # lệnh quản lý database
  tests/             # 27 test API
```

## 1. Cài đặt (một lần)

Cần [uv](https://docs.astral.sh/uv/) (máy này đã có).

```bash
cd backend
```

```bash
uv sync
```

Mở `backend/.env`, điền **DB_PASSWORD** (mật khẩu database Supabase). Quên thì vào
Dashboard → Project Settings → Database → **Reset database password**.

```bash
uv run python manage.py migrate
```

Lần đầu chạy trên project hiện tại sẽ in `Schema v2.1 đã có sẵn trong database -> chỉ ghi nhận baseline.`
(không tạo lại, không đụng dữ liệu), rồi áp migration `chi_nhan_timezone_iana` (chỉ nhận múi giờ đúng tên IANA
như `Asia/Ho_Chi_Minh`; trước đó `UTC+7` lọt qua và bị Postgres hiểu ngược thành UTC-7). Sau đó:

```bash
uv run python manage.py check
```

phải in `Models và database khớp nhau.`

## 2. Tạo / sửa bảng bằng Python

Ví dụ thêm bảng `feedbacks` (user chấm điểm một cuộc trò chuyện):

**Bước 1** – tạo `app/models/feedback.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, uuid_pk


class Feedback(Base):
    __tablename__ = "feedbacks"
    __table_args__ = (
        # conversation phải thuộc đúng user này (giống các bảng khác)
        ForeignKeyConstraint(["conversation_id", "user_id"], ["conversations.id", "conversations.user_id"],
                             ondelete="CASCADE"),
        CheckConstraint("rating between 1 and 5", name="feedbacks_rating_chk"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)        # có "| None" = cho phép NULL
    created_at: Mapped[datetime] = created_at()
```

**Bước 2** – thêm vào `app/models/__init__.py`:

```python
from app.models.feedback import Feedback
```

**Bước 3** – sinh file migration (so models với database thật):

```bash
uv run python manage.py make "them bang feedbacks"
```

Mở file mới trong `migrations/versions/` xem lại (bảng, cột, khóa ngoại). Bảng mới **tự được bật RLS**
và thu quyền của `anon`/`authenticated`, nên mobile không đọc trực tiếp được cho tới khi bạn thêm policy.

**Bước 4** – áp lên Supabase:

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

Đặt `uv run python` trước mỗi lệnh, chạy trong thư mục `backend/`.

**Quy tắc:** chỉ đổi schema qua Python. Không sửa bảng bằng Table Editor của Supabase hay `supabase db push`,
nếu không `check` sẽ báo lệch.

## 3. Chạy API

```bash
uv run fastapi dev app/main.py
```

Mở http://127.0.0.1:8000/docs để thử API. Mọi API (trừ `/health`) cần header
`Authorization: Bearer <access_token>`; mobile lấy token từ `supabase.auth.getSession()`.

| API | |
|---|---|
| `GET /health` | kiểm tra kết nối database |
| `GET /me`, `PATCH /me`, `PATCH /me/settings` | hồ sơ, cài đặt |
| `GET /agents` | agent user được dùng (public + được cấp quyền) |
| `GET/POST /conversations` | danh sách (ghim trước, mới nhất trước) / tạo mới |
| `GET/PATCH/DELETE /conversations/{id}` | xem, đổi tên, ghim, lưu trữ, xóa mềm |
| `GET /conversations/{id}/messages?before_seq=&limit=` | tin nhắn, mới nhất trước, phân trang theo `next_before_seq` |
| `POST /conversations/{id}/messages` | gửi tin `{content, idempotency_key}`, chờ agent trả lời |
| `GET /search?q=` | tìm không dấu trong lịch sử chat |

Gửi tin: app tự sinh `idempotency_key` (UUID) cho mỗi lần bấm gửi. Mất mạng gửi lại cùng key thì
không tạo tin trùng. Mỗi cuộc trò chuyện chỉ một câu trả lời đang chạy; gửi chồng thì nhận `409`.

### GoClaw

`GOCLAW_MODE=mock` (mặc định) trả lời giả để làm app trước. Khi có GoClaw thật:

1. Lưu API key vào Vault và sửa `base_url`, `goclaw_agent_id` (xem `docs/SUPABASE_SETUP.md` mục 3).
2. Đặt `GOCLAW_MODE=openai`.

Client hiện gọi `POST {base_url}/v1/chat/completions` với `model = goclaw_agent_id` và header
`x-openclaw-session-key` = id cuộc trò chuyện. Đây là **giả định** theo kiểu OpenClaw (chưa tìm được tài liệu
API của GoClaw); kiểm tra với GoClaw thật rồi chỉnh hàm `_send_openai` trong `app/goclaw.py` nếu khác.

## 4. Test

Test chạy trên một Postgres riêng, **không** chạy trên Supabase thật:

```bash
TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:54329/postgres uv run pytest
```

(database test cần có schema auth/storage giả lập như Supabase, rồi `manage.py migrate` + `seed`).

## 5. Chưa làm

- Upload file đính kèm (signed upload URL), xóa tài khoản: cần thêm `SUPABASE_SERVICE_ROLE_KEY`.
- Trả lời dạng streaming (hiện chờ trả lời xong mới trả về).
- Worker lịch hẹn, push notification, outbox (hàm SQL đã có sẵn trong database).
