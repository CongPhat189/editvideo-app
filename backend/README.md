# Edit Video App – Backend (FastAPI)

## Cấu trúc thư mục

```text
backend/
├── app/
│   ├── main.py                  # Entry point FastAPI
│   ├── api/
│   │   ├── deps.py              # Dependencies (get_db, get_current_user)
│   │   └── v1/
│   │       ├── router.py        # Tổng hợp API routes
│   │       └── endpoints/
│   │           ├── auth.py      # Đăng nhập, đăng ký, Google, quên mật khẩu
│   │           ├── users.py     # Danh sách người dùng
│   │           ├── dashboard.py
│   │           ├── videos.py    # Dựng video AI
│   │           ├── schedule.py  # Lịch đăng
│   │           ├── analytics.py
│   │           ├── platforms.py # Kênh + connectors
│   │           └── publishing.py
│   ├── core/
│   │   ├── config.py            # Đọc biến môi trường (.env)
│   │   ├── security.py          # JWT, hash mật khẩu
│   │   └── logging.py
│   ├── models/                  # SQLAlchemy models
│   │   ├── user.py              # User, Account
│   │   ├── schedule.py
│   │   └── integration.py
│   ├── schemas/                 # Pydantic schemas
│   │   ├── auth.py, user.py, content.py, schedule.py, integration.py
│   ├── services/                # Business logic
│   │   ├── auth_service.py, user_service.py, schedule_service.py, integration_service.py
│   ├── repositories/            # Truy vấn database
│   │   ├── user_repository.py, schedule_repository.py, integration_repository.py
│   ├── db/
│   │   ├── session.py           # Kết nối database, get_db
│   │   ├── base.py              # SQLAlchemy Base
│   │   ├── init_db.py           # Tạo bảng + dữ liệu demo
│   │   └── mock_data.py         # Dữ liệu demo trong RAM
│   ├── utils/helpers.py
│   └── integrations/
│       ├── goclaw.py            # Kết nối GoClaw API
│       └── external_api.py
├── tests/
├── alembic/                     # Database migrations
├── .env / .env.example
├── alembic.ini
├── requirements.txt
├── pyproject.toml
└── Dockerfile
```

## Cài đặt & chạy

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # nếu chưa có .env

uvicorn app.main:app --reload --port 4000
# hoặc: python -m app.main
```

Mở http://localhost:4000/docs để xem toàn bộ API.

Tài khoản demo: `abc@gmail.com` / `123456`.

## Chạy test

```bash
pytest
```

## Migration (Alembic)

```bash
alembic revision --autogenerate -m "mo ta thay doi"
alembic upgrade head
```

## API chính

- `GET /api/health`
- `POST /api/auth/register` · `POST /api/auth/login` · `POST /api/auth/google` · `POST /api/auth/forgot-password`
- `GET /api/users`
- `GET /api/dashboard`
- `POST /api/videos/generate`
- `GET /api/schedule` · `POST /api/schedule`
- `GET /api/analytics`
- `GET /api/platforms` · `GET /api/connectors` · `POST /api/connectors/{provider}`
- `POST /api/publishing`

## Ghi chú

- Videos, analytics, publishing hiện dùng dữ liệu demo trong RAM (`app/db/mock_data.py`), reset khi restart.
- User, lịch đăng, connectors lưu trong SQLite `connector_screen.db`.
- Frontend: tạo `.env` trong thư mục FE với `VITE_API_BASE_URL=http://localhost:4000`.
