# GoClaw Mobile – Database v2.1 trên Supabase

## Cấu trúc file

```text
supabase/
  migrations/
    20261102000100_schema.sql     # 16 bảng, index, constraint, trigger, hàm worker/RPC
    20261102000200_security.sql   # RLS, quyền truy cập, Realtime
    20261102000300_storage.sql    # 3 bucket + policy storage
  seed.sql                        # workspace + agent mẫu (sửa REPLACE_ME trước khi dùng thật)
backend/                          # FastAPI + SQLAlchemy models + Alembic (xem backend/README.md)
docs/
  ERD.md, erd.png, erd.svg, erd.html
```

## Project đang dùng

| | |
|---|---|
| Project | `editvideo-app` – ref `uzgccexajrahaumdofqy` |
| Region | `eu-west-2` (London) – người dùng ở VN sẽ có độ trễ cao hơn Singapore (`ap-southeast-1`); region không đổi được sau khi tạo |
| Dashboard | https://supabase.com/dashboard/project/uzgccexajrahaumdofqy |
| API URL | `https://uzgccexajrahaumdofqy.supabase.co` |
| Đã đẩy | 3 migration + seed (2026-11-02), Security/Performance Advisor: chỉ 1 cảnh báo có chủ đích (`register_device` là SECURITY DEFINER để gỡ push token khỏi tài khoản cũ) |

**Từ giờ mọi thay đổi bảng đi qua Python** (`backend/app/models` → `uv run python manage.py make "..."` → `migrate`), xem [backend/README.md](../backend/README.md).
3 file trong `supabase/migrations/` là baseline (Alembic revision `0001` chạy lại đúng 3 file này trên database mới). Đừng thêm file mới vào đó và đừng `supabase db push` nữa, để chỉ có **một** nơi quản lý schema.

## Kiến trúc v2.1 (khác spec ở phần đăng nhập)

```text
Mobile (Expo)
  ├─ supabase-js ──> Supabase Auth      đăng ký / đăng nhập SĐT + mật khẩu, OTP, quên mật khẩu
  ├─ supabase-js ──> Postgres (RLS)     đọc dữ liệu của mình + Realtime đồng bộ nhiều máy
  │                                     ghi: profile, settings, register_device()
  └─ HTTPS + JWT ──> FastAPI            chat, GoClaw, lịch hẹn, upload, đăng bài
                        └─ service role / postgres ──> Postgres, Storage, Vault
```

- Mobile chỉ giữ **URL + anon (publishable) key**: key này công khai, RLS bảo vệ dữ liệu.
- FastAPI verify JWT của Supabase (JWKS: `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json`), lấy `sub` làm `user_id`.
- GoClaw API key, OAuth token mạng xã hội: lưu **Supabase Vault**, bảng chỉ giữ `*_secret_id`.

---

## 1. Đẩy schema lên Supabase (project mới)

### Cách A – Python (khuyên dùng)

Điền `backend/.env` rồi:

```bash
uv run python manage.py migrate
```

```bash
uv run python manage.py seed
```

### Cách B – Supabase CLI

```bash
npx supabase login
```

```bash
npx supabase link --project-ref <PROJECT_REF>
```

```bash
npx supabase db push --include-seed
```

### Cách C – SQL Editor

Dashboard → SQL Editor, chạy lần lượt 3 file trong `supabase/migrations/` rồi `supabase/seed.sql`.

Dùng cách B hoặc C xong vẫn chạy `uv run python manage.py migrate` một lần: Alembic thấy schema đã có sẵn thì chỉ ghi nhận phiên bản.

## 2. Bật đăng nhập bằng số điện thoại

Dashboard → **Authentication → Sign In / Providers → Phone**:

1. Bật **Phone**.
2. Chọn nhà cung cấp SMS (Twilio, Vonage, MessageBird, Textlocal…) và điền thông tin. Cần cho OTP xác minh SĐT và quên mật khẩu.
3. Lúc dev chưa có SMS: thêm **Test phone numbers** (vd `84900000001=123456`) để đăng nhập không tốn SMS.

Mobile:

```ts
await supabase.auth.signUp({ phone: '+84912345678', password, options: { data: { full_name: 'Nguyễn Văn A' } } })
await supabase.auth.verifyOtp({ phone: '+84912345678', token: '123456', type: 'sms' })
await supabase.auth.signInWithPassword({ phone: '+84912345678', password })
```

`profiles` và `user_settings` tự được tạo khi đăng ký (trigger `on_auth_user_created`).

## 3. Lưu GoClaw API key vào Vault

Chạy trong SQL Editor (thay giá trị thật):

```sql
update public.goclaw_workspaces
   set base_url = 'https://goclaw.cua-ban.com',
       api_key_secret_id = vault.create_secret('<GOCLAW_API_KEY>', 'goclaw_default_api_key')
 where name = 'default';

update public.agents set goclaw_agent_id = '<ID thật>' where goclaw_agent_id = 'REPLACE_ME_general_assistant';
```

FastAPI đọc key:

```sql
select decrypted_secret from vault.decrypted_secrets where id = :api_key_secret_id;
```

## 4. Biến môi trường

Mobile (`.env` của Expo, công khai được):

```env
EXPO_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=<anon / publishable key>
```

FastAPI: `backend/.env` (bí mật, không commit, mẫu ở `backend/.env.example`):

```env
DATABASE_URL=postgresql://postgres.<ref>@aws-0-<region>.pooler.supabase.com:5432/postgres
DB_PASSWORD=<mật khẩu database>
SUPABASE_URL=https://<ref>.supabase.co
GOCLAW_MODE=mock
```

- Session pooler (port 5432) chạy được trên IPv4. Driver là psycopg 3; nếu chuyển sang Transaction pooler (6543) thì thêm `prepare_threshold=None`.
- Mật khẩu để riêng ở `DB_PASSWORD` nên không cần mã hóa ký tự đặc biệt trong URL.
- Kết nối `postgres` **bỏ qua RLS** → mọi query trong FastAPI phải có `WHERE user_id = :user_id_tu_jwt` (đã làm trong `backend/app/routers`, có test chặn đọc dữ liệu người khác).

---

## 5. Cách backend dùng database

### Gửi tin nhắn

```text
POST /chat/send {conversation_id, content, idempotency_key, attachment_ids[]}
1. BEGIN
   - Kiểm tra conversation thuộc user, chưa xóa; can_use_agent(user, agent) còn đúng
   - INSERT messages (role=user, status=completed, idempotency_key)
       trùng idx_messages_idempotency  -> client retry, trả kết quả cũ
   - UPDATE message_attachments SET message_id, status='attached' WHERE id = ANY(:ids) AND status='uploaded'
   - INSERT messages (role=assistant, status=processing, reply_to_message_id = tin user)
       trùng uq_messages_one_inflight_reply -> 409 "AI đang trả lời"
   COMMIT
2. Gọi GoClaw với goclaw_session_id (stream SSE về mobile)
3. UPDATE tin assistant: content, status=completed, model, input_tokens, output_tokens, cost_usd
   Lỗi -> status=failed, error_message (mobile có nút gửi lại)
```

Tin assistant kẹt `processing` (server chết giữa chừng) sẽ chặn conversation, nên trước bước 1 chạy:

```sql
update messages set status = 'failed', error_message = 'timeout'
 where conversation_id = :cid and role = 'assistant'
   and status in ('pending', 'processing') and updated_at < now() - interval '5 minutes';
```

### Phân trang tin nhắn

```sql
select * from messages
 where conversation_id = :cid and (:cursor is null or seq < :cursor)
 order by seq desc
 limit 30;
```

### Danh sách chat

```sql
select * from conversations
 where user_id = :uid and deleted_at is null and status = 'active'
 order by pinned_at desc nulls last, coalesce(last_message_at, created_at) desc, id
 limit 30;
```

### Upload file

```text
1. POST /attachments {file_name, mime_type, file_size}
   -> INSERT message_attachments (status=pending_upload, file_path = {user_id}/{attachment_id}/{file_name})
   -> trả signed upload URL (storage.from('chat-attachments').createSignedUploadUrl(path))
2. Mobile upload thẳng lên Storage
3. POST /attachments/{id}/complete -> kiểm tra file tồn tại -> status=uploaded
4. Gửi tin kèm attachment_ids
Job dọn: status <> 'attached' AND created_at < now() - 24h -> xóa file Storage + xóa dòng
```

### Thiết bị & push

- Mobile gọi `supabase.rpc('register_device', {...})` sau khi đăng nhập và mỗi lần mở app; khi đăng xuất gọi lại với `p_push_token: null`.
- Gửi thông báo: INSERT `notifications` → với mỗi device có `push_token` INSERT `notification_deliveries` → gửi Expo → lưu `expo_ticket_id`.
- Job đọc push receipt: lỗi `DeviceNotRegistered` → `UPDATE devices SET push_token = null`.

### Worker lịch hẹn (VPS)

```python
# Bước 1 – tạo run cho task đến hạn (1 transaction)
tasks = SELECT id, next_run_at, recurrence_rule, timezone, ends_at FROM scheduled_tasks
        WHERE status = 'active' AND next_run_at <= now()
        ORDER BY next_run_at LIMIT 50 FOR UPDATE SKIP LOCKED
for t in tasks:
    nxt = rrulestr(t.recurrence_rule, dtstart=t.next_run_at in t.timezone).after(max(now, t.next_run_at)) if t.recurrence_rule else None
    if nxt and t.ends_at and nxt > t.ends_at: nxt = None
    SELECT enqueue_task_run(t.id, t.next_run_at, nxt)   -- nxt NULL -> task 'finished'
COMMIT

# Bước 2 – chạy
for run in SELECT * FROM claim_due_task_runs('worker-1', 10):
    INSERT scheduled_task_logs (run_id, attempt_number = run.attempts, status='processing')
    if run.external_ref: đã đăng rồi -> đánh dấu completed, KHÔNG đăng lại
    gọi GoClaw / API mạng xã hội (gửi kèm run.idempotency_key nếu hỗ trợ)
    thành công -> UPDATE run SET status='completed', external_ref, result, finished_at
    lỗi tạm thời và chắc chắn bên ngoài chưa nhận -> status='retrying', next_retry_at = now() + backoff
    hết lượt hoặc không chắc -> status='failed'
    -> INSERT notifications cho user
```

Run kẹt `processing` (worker chết) không tự chạy lại; kiểm tra bằng `idx_task_runs_processing` rồi đối soát thủ công.

### Xóa cuộc trò chuyện

- Xóa mềm: `UPDATE conversations SET status='deleted', deleted_at=now()`.
- Job purge sau 30 ngày: xóa file Storage của các attachment → `DELETE FROM conversations WHERE deleted_at < now() - interval '30 days'` (messages, attachments cascade).

### Xóa tài khoản (bắt buộc với App Store)

1. Mobile: `POST /account/delete` → `UPDATE profiles SET deletion_requested_at = now()`, đăng xuất mọi máy.
2. Job (sau N ngày cho phép khôi phục): xóa file trong `avatars/{uid}`, `chat-attachments/{uid}`, `scheduled-media/{uid}`; xóa secret Vault của social_accounts; xóa session GoClaw nếu GoClaw hỗ trợ; cuối cùng `supabase.auth.admin.deleteUser(uid)` → toàn bộ dữ liệu trong DB tự xóa theo CASCADE.

### Outbox (khuyên dùng khi lên production)

Ghi `outbox_events` trong cùng transaction với dữ liệu chính (vd `goclaw.send_message` khi tạo tin assistant), worker gọi `claim_outbox_events()` để xử lý / đối soát nếu FastAPI chết giữa chừng.

---

## 6. Mobile được làm gì trực tiếp với Supabase

| Hành động | Cách |
|---|---|
| Đăng ký, đăng nhập, OTP, quên mật khẩu, đăng xuất | `supabase.auth.*` |
| Đọc profile, settings, agents, conversations, messages, tasks, notifications | `supabase.from(...).select()` (RLS lọc theo user) |
| Đổi tên, avatar | `update profiles set full_name, avatar_path` + upload `avatars/{uid}/{uuid}.jpg` |
| Đổi cài đặt | `update user_settings` |
| Đánh dấu đã đọc thông báo | `update notifications set read_at` |
| Đăng ký thiết bị / push token | `rpc('register_device')` |
| Tìm kiếm tin nhắn không dấu | `rpc('search_messages', { p_query })` |
| Thống kê token | `from('v_usage_daily').select()` |
| Đồng bộ realtime | `supabase.channel(...).on('postgres_changes', { table: 'messages' })` |
| Mọi thứ khác (chat, tạo/sửa/xóa conversation, task, upload file chat, đăng bài) | gọi FastAPI |

## 7. Thay đổi so với spec v2.0

| Spec v2.0 | v2.1 | Lý do |
|---|---|---|
| `users` + `password_hash`, `user_sessions` | `auth.users` + `profiles` | Không tự viết OTP, quên mật khẩu, chống dò mật khẩu, xoay token |
| `messages` sắp theo `created_at` | thêm `seq` | 2 tin cùng transaction trùng `created_at` → sai thứ tự |
| — | unique "1 câu trả lời đang chạy / conversation" | Chặn gửi chồng vào cùng GoClaw session |
| token trong `metadata` | cột `model`, `input_tokens`, `output_tokens`, `cost_usd` + view `v_usage_daily` | Thống kê nhanh, chính xác |
| attachment bắt buộc có message | `message_id` nullable + `status`, `user_id` | Upload trước khi gửi |
| `devices` không có định danh máy | `installation_id` + RPC `register_device` | Không nhân bản thiết bị, token tự chuyển khi đổi tài khoản |
| avatar `{user_id}/avatar.jpg` | `{user_id}/{uuid}.jpg` | Không dính cache khi đổi ảnh |
| `scheduled_tasks` vừa định nghĩa vừa trạng thái | `scheduled_tasks` + `scheduled_task_runs` + logs theo run | Lịch lặp có lịch sử từng lần, retry độc lập |
| — | `social_accounts` (token trong Vault), `external_ref` | Đăng bài đa nền tảng, không đăng trùng |
| — | `goclaw_workspaces` | Nhiều GoClaw workspace |
| — | `user_agent_access` + `agents.visibility` + trigger | Chặn agent chưa được cấp quyền ngay trong DB |
| — | `notifications`, `notification_deliveries` | Hộp thư trong app + theo dõi push Expo |
| — | `outbox_events` | Đối soát khi gọi GoClaw bị gián đoạn |
| tìm kiếm có dấu | `f_unaccent` + trigram | "da nang" tìm ra "Đà Nẵng" |
| `goclaw_session_id` unique toàn cục | unique theo `(agent_id, goclaw_session_id)` | Session ID chỉ có nghĩa trong một agent/workspace |
| — | `title_source` | AI đổi tên tự động không ghi đè tên người dùng đặt |

## 8. Còn cần bạn xác nhận

- Cơ chế session của GoClaw (tạo trước hay ở tin đầu, có API xóa không) – ảnh hưởng luồng tạo conversation và xóa tài khoản.
- Nhà cung cấp SMS cho OTP.
- Số ngày giữ dữ liệu sau khi xóa mềm (mặc định đề xuất 30 ngày).
