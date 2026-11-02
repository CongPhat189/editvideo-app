# GoClaw Mobile – Database trên Supabase

Supabase chỉ dùng làm **PostgreSQL**. Tài khoản, mật khẩu, JWT do backend FastAPI tự quản lý; không dùng Supabase Auth, không có bước xác thực số điện thoại.

## Cấu trúc file

```text
backend/app/models.py             # 8 bảng viết bằng Python (nguồn chuẩn của schema)
backend/alembic/versions/         # migration, đầu tiên là 0003_schema_8_bang
supabase/seed.sql                 # 3 agent mẫu
docs/ERD.md, erd.png, erd.svg, erd.html
```

## Project đang dùng

| | |
|---|---|
| Project | `editvideo-app` – ref `uzgccexajrahaumdofqy` |
| Region | `eu-west-2` (London) – người dùng ở VN sẽ có độ trễ cao hơn Singapore (`ap-southeast-1`); region không đổi được sau khi tạo |
| Dashboard | https://supabase.com/dashboard/project/uzgccexajrahaumdofqy |
| Hiện trạng | Đã áp migration `0004`: 8 bảng, RLS bật hết, anon key bị từ chối, Security/Performance Advisor không có cảnh báo |

## Kiến trúc

```text
Mobile (Expo) ── HTTPS + JWT do backend cấp ──> FastAPI ── postgres ──> Supabase Postgres
                                                  └──> GoClaw
```

- Mobile chỉ gọi FastAPI, không cần key nào của Supabase.
- Kết nối `postgres` **bỏ qua RLS** → mọi query trong FastAPI phải lọc theo `user_id` lấy từ token.
- API key của agent mã hóa bằng Fernet (`AGENT_KEY_ENCRYPTION_KEY`) rồi lưu vào `agents.key`.

## Đổi schema

Chỉ đổi qua Python: sửa `backend/app/models.py`, rồi trong thư mục `backend/`:

```bash
uv run python manage.py make "mo ta thay doi"
```

```bash
uv run python manage.py migrate
```

Đừng sửa bảng bằng Table Editor và đừng dùng `supabase db push`. Hướng dẫn đầy đủ ở [backend/README.md](../backend/README.md).

## Dựng trên project mới

1. Điền `backend/.env` theo `backend/.env.example`.
2. Chạy lần lượt:

```bash
uv run python manage.py migrate
```

```bash
uv run python manage.py seed
```

3. Đặt domain và key cho agent:

```bash
uv run python manage.py agent "Trợ lý chung" --domain https://goclaw.cua-ban.com --set-key
```

## Việc còn lại trên Dashboard

- Tắt đăng ký Supabase Auth (Authentication → Sign In / Providers → Allow new users to sign up), vì app không dùng. Không cần bật Phone, không cần nhà cung cấp SMS.
- 3 bucket Storage cũ (`avatars`, `chat-attachments`, `scheduled-media`) còn đó nhưng đã bỏ policy nên không ai upload được. Khi làm upload sẽ đi qua backend; không dùng thì xóa trên Dashboard.
