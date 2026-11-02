# ERD – GoClaw Mobile Database

Sơ đồ khớp 1:1 với `backend/app/models.py` (`manage.py check` so models với database thật).
Ảnh: `docs/erd.png` (PNG) và `docs/erd.svg` (vector). Bản xem trên trình duyệt: `docs/erd.html`.

```mermaid
erDiagram
    users ||--|| user_settings : "cài đặt"
    users ||--o{ conversations : "sở hữu"
    users ||--o{ messages : "chủ sở hữu (composite FK)"
    users ||--o{ scheduled_tasks : "tạo"
    agents ||--o{ conversations : "được dùng trong"
    agents |o--o{ scheduled_tasks : "thực thi bởi"
    conversations ||--o{ messages : "chứa"
    conversations |o--o{ scheduled_tasks : "ngữ cảnh AI"
    messages |o--o{ messages : "reply_to"
    messages ||--o{ message_attachments : "đính kèm"
    scheduled_tasks ||--o{ scheduled_task_logs : "nhật ký"

    users {
        uuid id PK
        varchar full_name
        varchar phone UK "E.164"
        text password_hash "Argon2id"
        text avatar_url
        varchar status "active|suspended|deleted"
        timestamptz created_at
        timestamptz updated_at
        timestamptz last_login_at
        timestamptz deleted_at
    }

    user_settings {
        uuid id PK
        uuid user_id FK,UK
        varchar theme "light|dark|system"
        varchar language
        varchar timezone "tên IANA"
        boolean notification_enabled
        jsonb settings_json
        timestamptz created_at
        timestamptz updated_at
    }

    agents {
        uuid id PK
        varchar name
        text key "API key - mã hoá khi lưu"
        varchar domain "vd: https://goclaw.abc.com"
        timestamptz created_at
        timestamptz updated_at
    }

    conversations {
        uuid id PK
        uuid user_id FK
        uuid agent_id FK
        varchar title
        varchar goclaw_session_id UK "nullable"
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
        uuid conversation_id FK
        uuid user_id FK
        varchar role "user|assistant|system|tool"
        text content
        varchar content_type "text|image|file|audio|video"
        varchar goclaw_message_id
        uuid reply_to_message_id FK
        varchar status "pending..cancelled"
        uuid idempotency_key UK "per user"
        text error_message
        jsonb metadata "tokens, model, tools"
        timestamptz favorited_at
        timestamptz created_at
        timestamptz updated_at
    }

    message_attachments {
        uuid id PK
        uuid message_id FK
        varchar file_name
        text file_path UK
        text file_url
        varchar mime_type
        bigint file_size
        timestamptz created_at
    }

    scheduled_tasks {
        uuid id PK
        uuid user_id FK
        uuid conversation_id FK "nullable"
        uuid agent_id FK "nullable"
        varchar task_name
        varchar task_type "send_message|execute_agent|..."
        jsonb payload
        timestamptz scheduled_at
        varchar timezone
        text recurrence_rule "RRULE"
        varchar status "scheduled..retrying"
        int attempts
        int max_attempts
        timestamptz next_retry_at
        text last_error
        varchar locked_by
        timestamptz locked_at
        timestamptz executed_at
        timestamptz completed_at
        timestamptz created_at
        timestamptz updated_at
    }

    scheduled_task_logs {
        uuid id PK
        uuid task_id FK
        int attempt_number
        varchar status
        jsonb request_payload
        jsonb response_payload
        text error_message
        timestamptz started_at
        timestamptz finished_at
        timestamptz created_at
    }
```

## Quan hệ và quy tắc xóa

| Quan hệ | Cardinality | FK | ON DELETE |
|---|---|---|---|
| users → user_settings | 1:1 | `user_settings.user_id` UNIQUE | CASCADE |
| users → conversations | 1:N | `conversations.user_id` | CASCADE |
| agents → conversations | 1:N | `conversations.agent_id` | RESTRICT |
| conversations → messages (đúng chủ sở hữu) | 1:N | `(conversation_id, user_id)` → `conversations(id, user_id)` | CASCADE |
| messages → messages (reply, cùng conversation) | 1:N | `(reply_to_message_id, conversation_id)` → `messages(id, conversation_id)` | SET NULL `reply_to_message_id` |
| messages → message_attachments | 1:N | `message_attachments.message_id` | CASCADE |
| users → scheduled_tasks | 1:N | `scheduled_tasks.user_id` | CASCADE |
| conversations → scheduled_tasks (đúng chủ sở hữu) | 1:N (tùy chọn) | `(conversation_id, user_id)` → `conversations(id, user_id)` | SET NULL `conversation_id` |
| agents → scheduled_tasks | 1:N (tùy chọn) | `scheduled_tasks.agent_id` | SET NULL |
| scheduled_tasks → scheduled_task_logs | 1:N | `scheduled_task_logs.task_id` | CASCADE |

## Những gì database tự bảo đảm

- **Đúng chủ sở hữu**: message và task không thể trỏ sang conversation của người khác (composite FK).
- **Thứ tự tin nhắn**: sắp theo `(created_at, id)`, API bảo đảm tin sau luôn có `created_at` lớn hơn tin trước.
- **Một câu trả lời AI đang chạy / conversation**: unique index `uq_messages_one_inflight_reply`.
- **Chống gửi trùng**: unique `(user_id, idempotency_key)`.
- **Timezone**: chỉ nhận đúng tên IANA, `UTC+7` bị từ chối.
- **Tìm kiếm không dấu**: "da nang" tìm ra "Đà Nẵng".
- **Data API đóng**: mọi bảng bật RLS, không có policy, không cấp quyền cho `anon` và `authenticated`.
