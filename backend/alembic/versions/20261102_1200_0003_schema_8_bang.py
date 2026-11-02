"""schema theo sơ đồ 8 bảng

users, user_settings, agents, conversations, messages, message_attachments, scheduled_tasks,
scheduled_task_logs. Backend tự quản lý tài khoản và JWT, không xác thực số điện thoại.

Revision ID: 0003
Revises:
Create Date: 2026-11-02
"""
from typing import Sequence, Union

from alembic import op

# Giữ id 0003 vì database Supabase đang ghi phiên bản này
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

HELPERS = r"""
create extension if not exists pg_trgm  with schema extensions;
create extension if not exists unaccent with schema extensions;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- Bỏ dấu tiếng Việt để tìm kiếm: "Xin Chào Đà Nẵng" -> "xin chao da nang"
create or replace function public.f_unaccent(text)
returns text
language sql
immutable parallel safe strict
set search_path = ''
as $$
  select extensions.unaccent('extensions.unaccent'::regdictionary, lower($1));
$$;

-- Chỉ nhận đúng tên IANA, vd Asia/Ho_Chi_Minh. "UTC+7" bị từ chối vì Postgres hiểu ngược thành UTC-7.
create or replace function public.validate_timezone()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.timezone !~ '^(posix|right)/'
     and exists (select 1 from pg_catalog.pg_timezone_names where name = new.timezone) then
    return new;
  end if;
  raise exception 'invalid time zone "%": dùng tên IANA, vd Asia/Ho_Chi_Minh', new.timezone
    using errcode = '22023';
end;
$$;

create or replace function public.sync_conversation_message_stats()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    update public.conversations
       set message_count   = message_count + 1,
           last_message_at = greatest(coalesce(last_message_at, new.created_at), new.created_at)
     where id = new.conversation_id;
    return new;
  elsif tg_op = 'DELETE' then
    update public.conversations
       set message_count = greatest(message_count - 1, 0)
     where id = old.conversation_id;
    return old;
  end if;
  return null;
end;
$$;
"""

SCHEMA = r"""
create table public.users (
  id             uuid primary key default gen_random_uuid(),
  full_name      varchar(150) not null,
  phone          varchar(20)  not null,
  password_hash  text         not null,
  avatar_url     text,
  status         varchar(20)  not null default 'active',
  created_at     timestamptz  not null default now(),
  updated_at     timestamptz  not null default now(),
  last_login_at  timestamptz,
  deleted_at     timestamptz,
  constraint users_phone_key     unique (phone),
  constraint users_full_name_chk check (length(btrim(full_name)) > 0),
  constraint users_phone_chk     check (phone ~ '^\+[1-9][0-9]{7,14}$'),
  constraint users_status_chk    check (status in ('active', 'suspended', 'deleted')),
  constraint users_deleted_chk   check ((status = 'deleted') = (deleted_at is not null))
);
create trigger trg_users_updated_at before update on public.users
  for each row execute function public.set_updated_at();

create table public.user_settings (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid not null references public.users (id) on delete cascade,
  theme                 varchar(20)  not null default 'system',
  language              varchar(10)  not null default 'vi',
  timezone              varchar(100) not null default 'Asia/Ho_Chi_Minh',
  notification_enabled  boolean      not null default true,
  settings_json         jsonb        not null default '{}'::jsonb,
  created_at            timestamptz  not null default now(),
  updated_at            timestamptz  not null default now(),
  constraint user_settings_user_id_key  unique (user_id),
  constraint user_settings_theme_chk    check (theme in ('light', 'dark', 'system')),
  constraint user_settings_settings_chk check (jsonb_typeof(settings_json) = 'object')
);
create trigger trg_user_settings_updated_at before update on public.user_settings
  for each row execute function public.set_updated_at();
create trigger trg_user_settings_timezone before insert or update of timezone on public.user_settings
  for each row execute function public.validate_timezone();

create table public.agents (
  id          uuid primary key default gen_random_uuid(),
  name        varchar(150) not null,
  key         text,                     -- API key đã mã hóa, không lưu bản gốc
  domain      varchar(255) not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create trigger trg_agents_updated_at before update on public.agents
  for each row execute function public.set_updated_at();

create table public.conversations (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references public.users (id) on delete cascade,
  agent_id           uuid not null references public.agents (id) on delete restrict,
  title              varchar(255),
  goclaw_session_id  varchar(255),
  status             varchar(20) not null default 'active',
  message_count      integer     not null default 0,
  last_message_at    timestamptz,
  pinned_at          timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  archived_at        timestamptz,
  deleted_at         timestamptz,
  constraint conversations_id_user_key           unique (id, user_id),
  constraint conversations_goclaw_session_id_key unique (goclaw_session_id),
  constraint conversations_status_chk    check (status in ('active', 'archived', 'deleted')),
  constraint conversations_msg_count_chk check (message_count >= 0),
  constraint conversations_archived_chk  check (status <> 'archived' or archived_at is not null),
  constraint conversations_deleted_chk   check ((status = 'deleted') = (deleted_at is not null))
);
create index idx_conversations_user_list on public.conversations
  (user_id, pinned_at desc nulls last, (coalesce(last_message_at, created_at)) desc, id) where deleted_at is null;
create index idx_conversations_user_status on public.conversations (user_id, status);
create index idx_conversations_agent on public.conversations (agent_id);
create trigger trg_conversations_updated_at before update on public.conversations
  for each row execute function public.set_updated_at();

create table public.messages (
  id                   uuid primary key default gen_random_uuid(),
  conversation_id      uuid not null,
  user_id              uuid not null,
  role                 varchar(20) not null,
  content              text,
  content_type         varchar(30) not null default 'text',
  goclaw_message_id    varchar(255),
  reply_to_message_id  uuid,
  status               varchar(20) not null default 'pending',
  idempotency_key      uuid,
  error_message        text,
  metadata             jsonb not null default '{}'::jsonb,
  favorited_at         timestamptz,
  created_at           timestamptz not null default clock_timestamp(),
  updated_at           timestamptz not null default now(),
  constraint messages_id_conversation_key unique (id, conversation_id),
  constraint messages_conversation_owner_fk foreign key (conversation_id, user_id)
    references public.conversations (id, user_id) on delete cascade,
  constraint messages_reply_to_fk foreign key (reply_to_message_id, conversation_id)
    references public.messages (id, conversation_id) on delete set null (reply_to_message_id),
  constraint messages_role_chk         check (role in ('user', 'assistant', 'system', 'tool')),
  constraint messages_content_type_chk check (content_type in ('text', 'image', 'file', 'audio', 'video')),
  constraint messages_status_chk       check (status in ('pending', 'processing', 'completed', 'failed', 'cancelled')),
  constraint messages_metadata_chk     check (jsonb_typeof(metadata) = 'object')
);
create index idx_messages_conversation_created on public.messages (conversation_id, created_at desc, id desc);
create index idx_messages_user_created on public.messages (user_id, created_at desc);
create unique index idx_messages_idempotency on public.messages (user_id, idempotency_key)
  where idempotency_key is not null;
create unique index uq_messages_one_inflight_reply on public.messages (conversation_id)
  where role = 'assistant' and status in ('pending', 'processing');
create index idx_messages_reply_to on public.messages (reply_to_message_id) where reply_to_message_id is not null;
create index idx_messages_content_search on public.messages
  using gin (public.f_unaccent(content) extensions.gin_trgm_ops);
create trigger trg_messages_updated_at before update on public.messages
  for each row execute function public.set_updated_at();
create trigger trg_messages_sync_conversation after insert or delete on public.messages
  for each row execute function public.sync_conversation_message_stats();

create table public.message_attachments (
  id          uuid primary key default gen_random_uuid(),
  message_id  uuid not null references public.messages (id) on delete cascade,
  file_name   varchar(255) not null,
  file_path   text not null,
  file_url    text,
  mime_type   varchar(100) not null,
  file_size   bigint not null,
  created_at  timestamptz not null default now(),
  constraint message_attachments_file_path_key unique (file_path),
  constraint message_attachments_size_chk check (file_size >= 0)
);
create index idx_attachments_message on public.message_attachments (message_id);

create table public.scheduled_tasks (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references public.users (id) on delete cascade,
  conversation_id  uuid,
  agent_id         uuid references public.agents (id) on delete set null,
  task_name        varchar(255) not null,
  task_type        varchar(50)  not null,
  payload          jsonb        not null,
  scheduled_at     timestamptz  not null,
  timezone         varchar(100) not null default 'Asia/Ho_Chi_Minh',
  recurrence_rule  text,
  status           varchar(20)  not null default 'scheduled',
  attempts         integer      not null default 0,
  max_attempts     integer      not null default 3,
  next_retry_at    timestamptz,
  last_error       text,
  locked_by        varchar(100),
  locked_at        timestamptz,
  executed_at      timestamptz,
  completed_at     timestamptz,
  created_at       timestamptz  not null default now(),
  updated_at       timestamptz  not null default now(),
  constraint scheduled_tasks_conversation_owner_fk foreign key (conversation_id, user_id)
    references public.conversations (id, user_id) on delete set null (conversation_id),
  constraint scheduled_tasks_type_chk check (task_type in ('send_message', 'execute_agent', 'execute_workflow', 'publish_post')),
  constraint scheduled_tasks_status_chk check (status in ('scheduled', 'processing', 'completed', 'failed', 'cancelled', 'retrying')),
  constraint scheduled_tasks_attempts_chk check (attempts >= 0),
  constraint scheduled_tasks_max_attempts_chk check (max_attempts between 1 and 10),
  constraint scheduled_tasks_payload_chk check (jsonb_typeof(payload) = 'object'),
  constraint scheduled_tasks_retry_chk check (status <> 'retrying' or next_retry_at is not null)
);
create index idx_scheduled_tasks_due on public.scheduled_tasks (scheduled_at) where status = 'scheduled';
create index idx_scheduled_tasks_retry on public.scheduled_tasks (next_retry_at) where status = 'retrying';
create index idx_scheduled_tasks_processing on public.scheduled_tasks (locked_at) where status = 'processing';
create index idx_scheduled_tasks_user on public.scheduled_tasks (user_id, scheduled_at desc);
create index idx_scheduled_tasks_conversation on public.scheduled_tasks (conversation_id) where conversation_id is not null;
create trigger trg_scheduled_tasks_updated_at before update on public.scheduled_tasks
  for each row execute function public.set_updated_at();
create trigger trg_scheduled_tasks_timezone before insert or update of timezone on public.scheduled_tasks
  for each row execute function public.validate_timezone();

create table public.scheduled_task_logs (
  id                uuid primary key default gen_random_uuid(),
  task_id           uuid not null references public.scheduled_tasks (id) on delete cascade,
  attempt_number    integer not null,
  status            varchar(20) not null,
  request_payload   jsonb,
  response_payload  jsonb,
  error_message     text,
  started_at        timestamptz,
  finished_at       timestamptz,
  created_at        timestamptz not null default now(),
  constraint scheduled_task_logs_attempt_key unique (task_id, attempt_number),
  constraint scheduled_task_logs_attempt_chk check (attempt_number >= 1),
  constraint scheduled_task_logs_status_chk check (status in ('processing', 'completed', 'failed', 'cancelled'))
);

-- p_user_id bắt buộc: backend truyền id từ token đã kiểm tra
create function public.search_messages(p_user_id uuid, p_query text, p_limit integer default 30)
returns table (
  message_id uuid, conversation_id uuid, conversation_title varchar, role varchar, content text, created_at timestamptz
)
language sql
stable
set search_path = ''
as $$
  select m.id, m.conversation_id, c.title, m.role, m.content, m.created_at
    from public.messages m
    join public.conversations c on c.id = m.conversation_id
   where m.user_id = p_user_id
     and c.deleted_at is null
     and public.f_unaccent(m.content) like
         '%' || replace(replace(replace(public.f_unaccent(p_query), '\', '\\'), '%', '\%'), '_', '\_') || '%'
   order by m.created_at desc, m.id desc
   limit least(greatest(p_limit, 1), 100);
$$;

-- Mobile chỉ đi qua FastAPI. Bật RLS, không có policy và thu quyền: Data API với anon key không đọc được gì.
do $$
declare t text;
begin
  foreach t in array array['users', 'user_settings', 'agents', 'conversations', 'messages',
                           'message_attachments', 'scheduled_tasks', 'scheduled_task_logs',
                           'alembic_version'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon, authenticated', t);
  end loop;
end $$;
revoke all on all functions in schema public from public, anon, authenticated;
"""


def upgrade() -> None:
    # Chạy qua driver vì SQL có nhiều câu lệnh và ký tự % của LIKE
    cursor = op.get_bind().connection.dbapi_connection.cursor()
    cursor.execute(HELPERS)
    cursor.execute(SCHEMA)


def downgrade() -> None:
    raise NotImplementedError("Đây là migration đầu tiên: hạ xuống nghĩa là xóa sạch dữ liệu, phải tự làm có chủ đích.")
