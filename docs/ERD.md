# ERD – GoClaw Mobile Database v2.1

Sơ đồ khớp 1:1 với `supabase/migrations/20261102000100_schema.sql`.
Ảnh: `docs/erd.png` (PNG) và `docs/erd.svg` (vector). Bản xem trên trình duyệt: `docs/erd.html`.

```mermaid
erDiagram
    auth_users ||--|| profiles : "Supabase Auth"
    profiles ||--|| user_settings : "cài đặt"
    profiles ||--o{ devices : "sở hữu"
    profiles ||--o{ notifications : "nhận"
    notifications ||--o{ notification_deliveries : "đẩy tới"
    devices |o--o{ notification_deliveries : "thiết bị"
    goclaw_workspaces ||--o{ agents : "chứa"
    profiles ||--o{ user_agent_access : "được cấp"
    agents ||--o{ user_agent_access : "cấp cho"
    profiles ||--o{ conversations : "sở hữu"
    agents ||--o{ conversations : "dùng trong"
    conversations ||--o{ messages : "chứa"
    messages |o--o{ messages : "reply_to"
    profiles ||--o{ message_attachments : "upload"
    messages |o--o{ message_attachments : "đính kèm"
    profiles ||--o{ social_accounts : "liên kết"
    profiles ||--o{ scheduled_tasks : "tạo"
    conversations |o--o{ scheduled_tasks : "ngữ cảnh AI"
    agents |o--o{ scheduled_tasks : "thực thi bởi"
    social_accounts |o--o{ scheduled_tasks : "đăng lên"
    scheduled_tasks ||--o{ scheduled_task_runs : "mỗi lần chạy"
    scheduled_task_runs ||--o{ scheduled_task_logs : "mỗi lần thử"

    auth_users {
        uuid id PK
        text phone UK "Supabase quản lý"
        text encrypted_password
        timestamptz phone_confirmed_at
    }

    profiles {
        uuid id PK,FK "= auth.users.id"
        varchar full_name
        text avatar_path "{user_id}/{uuid}.jpg"
        varchar status "active|suspended"
        timestamptz deletion_requested_at
        timestamptz created_at
        timestamptz updated_at
    }

    user_settings {
        uuid id PK
        uuid user_id FK,UK
        varchar theme "light|dark|system"
        varchar language
        varchar timezone "đã kiểm tra hợp lệ"
        boolean notification_enabled
        jsonb settings_json
        timestamptz created_at
        timestamptz updated_at
    }

    devices {
        uuid id PK
        uuid user_id FK
        varchar installation_id UK "unique theo user"
        varchar device_name
        varchar platform "ios|android"
        varchar os_version
        varchar app_version
        text push_token UK "Expo"
        timestamptz push_token_updated_at
        timestamptz last_active_at
        timestamptz created_at
        timestamptz updated_at
    }

    notifications {
        uuid id PK
        uuid user_id FK
        varchar category "chat|task|system"
        varchar title
        text body
        jsonb data "deep link"
        timestamptz read_at
        timestamptz created_at
    }

    notification_deliveries {
        uuid id PK
        uuid notification_id FK
        uuid device_id FK "nullable"
        text push_token
        varchar status "queued|sent|delivered|failed"
        varchar expo_ticket_id
        varchar error_code
        text error_message
        timestamptz created_at
        timestamptz sent_at
        timestamptz checked_at
    }

    goclaw_workspaces {
        uuid id PK
        varchar name UK
        text base_url
        uuid api_key_secret_id "Vault"
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }

    agents {
        uuid id PK
        uuid workspace_id FK
        varchar name
        varchar goclaw_agent_id UK "unique theo workspace"
        text description
        text avatar_url
        varchar visibility "public|restricted"
        boolean is_active
        int sort_order
        timestamptz created_at
        timestamptz updated_at
    }

    user_agent_access {
        uuid user_id PK,FK
        uuid agent_id PK,FK
        timestamptz granted_at
        timestamptz expires_at
    }

    conversations {
        uuid id PK
        uuid user_id FK
        uuid agent_id FK
        varchar title
        varchar title_source "auto|user"
        varchar goclaw_session_id UK "unique theo agent"
        varchar status "active|archived|deleted"
        int message_count
        timestamptz last_message_at
        timestamptz pinned_at
        timestamptz created_at
        timestamptz updated_at
        timestamptz archived_at
        timestamptz deleted_at
    }

    messages {
        uuid id PK
        bigint seq UK "thứ tự, cursor"
        uuid conversation_id FK
        uuid user_id FK
        varchar role "user|assistant|system|tool"
        text content
        varchar content_type
        varchar goclaw_message_id
        uuid reply_to_message_id FK
        varchar status "pending..cancelled"
        uuid idempotency_key UK "theo user"
        text error_message
        varchar model
        int input_tokens
        int output_tokens
        numeric cost_usd
        jsonb metadata
        timestamptz favorited_at
        timestamptz created_at
        timestamptz updated_at
    }

    message_attachments {
        uuid id PK
        uuid user_id FK
        uuid message_id FK "NULL khi chưa gửi"
        varchar file_name
        text file_path UK "{user_id}/..."
        varchar mime_type
        bigint file_size
        varchar status "pending_upload|uploaded|attached"
        jsonb metadata
        timestamptz created_at
        timestamptz attached_at
    }

    social_accounts {
        uuid id PK
        uuid user_id FK
        varchar platform "facebook|tiktok|..."
        varchar external_account_id UK
        varchar display_name
        text avatar_url
        uuid access_token_secret_id "Vault"
        uuid refresh_token_secret_id "Vault"
        timestamptz token_expires_at
        text_array scopes
        varchar status "active|expired|revoked|error"
        text last_error
        timestamptz created_at
        timestamptz updated_at
    }

    scheduled_tasks {
        uuid id PK
        uuid user_id FK
        uuid conversation_id FK "nullable"
        uuid agent_id FK "nullable"
        uuid social_account_id FK "nullable"
        uuid group_id "đăng đa nền tảng"
        varchar task_name
        varchar task_type
        jsonb payload
        timestamptz scheduled_at "lần đầu"
        varchar timezone
        text recurrence_rule "RRULE"
        timestamptz ends_at
        timestamptz next_run_at
        varchar status "active|paused|finished|cancelled"
        int max_attempts
        int run_count
        timestamptz last_run_at
        timestamptz created_at
        timestamptz updated_at
    }

    scheduled_task_runs {
        uuid id PK
        uuid task_id FK
        uuid user_id FK
        timestamptz scheduled_for UK "theo task"
        varchar status "scheduled..retrying"
        int attempts
        int max_attempts
        timestamptz next_retry_at
        varchar locked_by
        timestamptz locked_at
        uuid idempotency_key UK
        varchar external_ref "post id phía ngoài"
        jsonb result
        text last_error
        timestamptz started_at
        timestamptz finished_at
        timestamptz created_at
        timestamptz updated_at
    }

    scheduled_task_logs {
        uuid id PK
        uuid run_id FK
        int attempt_number UK "theo run"
        varchar status
        jsonb request_payload
        jsonb response_payload
        text error_message
        timestamptz started_at
        timestamptz finished_at
        timestamptz created_at
    }

    outbox_events {
        uuid id PK
        varchar event_type
        varchar aggregate_type
        uuid aggregate_id
        jsonb payload
        varchar status "pending|processing|done|failed"
        int attempts
        timestamptz available_at
        varchar locked_by
        timestamptz locked_at
        text last_error
        timestamptz created_at
        timestamptz processed_at
    }
```

`outbox_events` đứng riêng (không có khóa ngoại): nó trỏ tới bản ghi bất kỳ qua `aggregate_type` + `aggregate_id`.

## Quan hệ và quy tắc xóa

| Quan hệ | Cardinality | FK | ON DELETE |
|---|---|---|---|
| auth.users → profiles | 1:1 | `profiles.id` | CASCADE (xóa tài khoản = xóa sạch dữ liệu) |
| profiles → user_settings | 1:1 | `user_settings.user_id` UNIQUE | CASCADE |
| profiles → devices | 1:N | `devices.user_id` | CASCADE |
| profiles → notifications | 1:N | `notifications.user_id` | CASCADE |
| notifications → notification_deliveries | 1:N | `notification_id` | CASCADE |
| devices → notification_deliveries | 1:N (tùy chọn) | `device_id` | SET NULL |
| goclaw_workspaces → agents | 1:N | `agents.workspace_id` | RESTRICT |
| profiles ↔ agents qua user_agent_access | N:M | PK `(user_id, agent_id)` | CASCADE |
| profiles → conversations | 1:N | `conversations.user_id` | CASCADE |
| agents → conversations | 1:N | `conversations.agent_id` | RESTRICT (tắt bằng `is_active`) |
| conversations → messages | 1:N | `(conversation_id, user_id)` → `conversations(id, user_id)` | CASCADE |
| messages → messages (reply) | 1:N | `(reply_to_message_id, conversation_id)` → `messages(id, conversation_id)` | SET NULL `reply_to_message_id` |
| messages → message_attachments | 1:N (tùy chọn) | `(message_id, user_id)` → `messages(id, user_id)` | CASCADE |
| profiles → social_accounts | 1:N | `social_accounts.user_id` | CASCADE |
| conversations → scheduled_tasks | 1:N (tùy chọn) | `(conversation_id, user_id)` → `conversations(id, user_id)` | SET NULL `conversation_id` |
| social_accounts → scheduled_tasks | 1:N (tùy chọn) | `(social_account_id, user_id)` → `social_accounts(id, user_id)` | SET NULL `social_account_id` |
| agents → scheduled_tasks | 1:N (tùy chọn) | `scheduled_tasks.agent_id` | SET NULL |
| scheduled_tasks → scheduled_task_runs | 1:N | `(task_id, user_id)` → `scheduled_tasks(id, user_id)` | CASCADE |
| scheduled_task_runs → scheduled_task_logs | 1:N | `scheduled_task_logs.run_id` | CASCADE |

## Những gì database tự bảo đảm (đã test, 64/64)

- **Đúng chủ sở hữu**: message, attachment, task, run, social account đều dùng composite FK `(…, user_id)` nên không thể trỏ sang dữ liệu người khác.
- **Thứ tự tin nhắn**: `seq` tăng dần tuyệt đối, kể cả khi 2 tin ghi cùng transaction.
- **Một câu trả lời AI đang chạy / conversation**: unique index `uq_messages_one_inflight_reply`.
- **Một GoClaw session ↔ một conversation** (theo agent): `uq_conversations_agent_session`.
- **Chống gửi trùng**: unique `(user_id, idempotency_key)`.
- **Quyền agent**: trigger chặn tạo conversation/task với agent không hoạt động hoặc `restricted` chưa được cấp.
- **Thiết bị**: một dòng mỗi `(user, installation_id)`, push token tự chuyển khi đổi tài khoản trên cùng máy.
- **File**: `file_path` phải nằm trong thư mục `{user_id}/`; attachment có thể tồn tại trước khi gửi tin.
- **Lịch hẹn**: mỗi lần chạy là một dòng `scheduled_task_runs` (unique theo `scheduled_for`), worker claim bằng `SKIP LOCKED`, task `paused` không bị chạy.
- **Timezone** không hợp lệ bị từ chối.
- **Tìm kiếm không dấu**: "da nang" tìm ra "Đà Nẵng".
- **Xóa tài khoản** (bắt buộc với App Store): xóa `auth.users` → mọi dữ liệu liên quan bị xóa.
