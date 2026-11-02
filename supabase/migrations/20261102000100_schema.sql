-- =====================================================================
-- GoClaw Mobile – Database Schema v2.1
-- Target: Supabase PostgreSQL 15+
--
-- Thay đổi chính so với spec v2.0:
--   * Đăng nhập dùng Supabase Auth (auth.users). Bảng users -> profiles,
--     bỏ user_sessions (Supabase quản lý phiên, refresh token, OTP).
--   * messages có cột seq để sắp xếp chính xác, cột token/chi phí riêng,
--     mỗi conversation chỉ một câu trả lời AI đang chạy.
--   * Upload file trước khi gửi tin (attachment có trạng thái riêng).
--   * Lịch hẹn tách định nghĩa (scheduled_tasks) và từng lần chạy
--     (scheduled_task_runs); thêm social_accounts cho đăng bài.
--   * Thêm goclaw_workspaces, user_agent_access, notifications,
--     notification_deliveries, outbox_events.
--
-- Quy ước: PK UUID; giá trị liệt kê dùng CHECK (dễ migrate hơn ENUM);
-- secret (API key, OAuth token) KHÔNG lưu ở đây mà lưu Supabase Vault,
-- bảng chỉ giữ id của secret.
-- =====================================================================

create extension if not exists pg_trgm  with schema extensions;
create extension if not exists unaccent with schema extensions;

-- ---------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------
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

-- Từ chối timezone không hợp lệ (vd 'Asia/Saigonn')
create or replace function public.validate_timezone()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  perform now() at time zone new.timezone;
  return new;
end;
$$;

-- =====================================================================
-- 1. profiles – Hồ sơ người dùng (1:1 với auth.users)
-- SĐT, mật khẩu, xác minh OTP, phiên đăng nhập nằm ở auth.users / auth.sessions.
-- =====================================================================
create table public.profiles (
  id                     uuid primary key references auth.users (id) on delete cascade,
  full_name              varchar(150) not null,
  avatar_path            text,                 -- avatars/{user_id}/{uuid}.jpg (không gồm tên bucket)
  status                 varchar(20)  not null default 'active',
  deletion_requested_at  timestamptz,          -- yêu cầu xóa tài khoản; job purge xóa hẳn sau N ngày
  created_at             timestamptz  not null default now(),
  updated_at             timestamptz  not null default now(),

  constraint profiles_full_name_chk check (length(btrim(full_name)) > 0),
  constraint profiles_status_chk    check (status in ('active', 'suspended')),
  constraint profiles_avatar_chk    check (avatar_path is null or avatar_path like id::text || '/%')
);

create trigger trg_profiles_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- =====================================================================
-- 2. user_settings – Cài đặt cá nhân (1:1)
-- =====================================================================
create table public.user_settings (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid not null references public.profiles (id) on delete cascade,
  theme                 varchar(20)  not null default 'system',
  language              varchar(10)  not null default 'vi',
  timezone              varchar(100) not null default 'Asia/Ho_Chi_Minh',
  notification_enabled  boolean      not null default true,
  settings_json         jsonb        not null default '{}'::jsonb,
  created_at            timestamptz  not null default now(),
  updated_at            timestamptz  not null default now(),

  constraint user_settings_user_id_key   unique (user_id),
  constraint user_settings_theme_chk     check (theme in ('light', 'dark', 'system')),
  constraint user_settings_settings_chk  check (jsonb_typeof(settings_json) = 'object')
);

create trigger trg_user_settings_updated_at
  before update on public.user_settings
  for each row execute function public.set_updated_at();

create trigger trg_user_settings_timezone
  before insert or update of timezone on public.user_settings
  for each row execute function public.validate_timezone();

-- Đăng ký qua Supabase Auth -> tự tạo profile + settings.
-- Mobile gọi: supabase.auth.signUp({ phone, password, options: { data: { full_name } } })
create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, full_name)
  values (
    new.id,
    left(coalesce(nullif(btrim(new.raw_user_meta_data ->> 'full_name'), ''), 'Người dùng'), 150)
  )
  on conflict (id) do nothing;

  insert into public.user_settings (user_id)
  values (new.id)
  on conflict (user_id) do nothing;

  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_auth_user();

-- =====================================================================
-- 3. devices – Thiết bị mobile
-- =====================================================================
create table public.devices (
  id                     uuid primary key default gen_random_uuid(),
  user_id                uuid not null references public.profiles (id) on delete cascade,
  installation_id        varchar(100) not null,   -- UUID app tự sinh lần đầu, lưu SecureStore
  device_name            varchar(150),
  platform               varchar(20)  not null,
  os_version             varchar(30),
  app_version            varchar(30),
  push_token             text,                    -- Expo Push Token
  push_token_updated_at  timestamptz,
  last_active_at         timestamptz,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),

  constraint devices_id_user_key           unique (id, user_id),
  constraint devices_user_installation_key unique (user_id, installation_id),
  constraint devices_platform_chk          check (platform in ('ios', 'android'))
);

-- Một push token chỉ thuộc một user tại một thời điểm
create unique index uq_devices_push_token
  on public.devices (push_token)
  where push_token is not null;

create trigger trg_devices_updated_at
  before update on public.devices
  for each row execute function public.set_updated_at();

-- Mobile gọi sau khi đăng nhập / mỗi lần mở app / khi đăng xuất (p_push_token = null):
--   supabase.rpc('register_device', { p_installation_id, p_platform, p_push_token, ... })
-- Nếu token đang gắn với tài khoản khác (đổi tài khoản trên cùng máy) thì gỡ ra trước.
create or replace function public.register_device(
  p_installation_id text,
  p_platform        text,
  p_device_name     text default null,
  p_push_token      text default null,
  p_app_version     text default null,
  p_os_version      text default null
)
returns public.devices
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
  v_row public.devices;
begin
  if v_uid is null then
    raise exception 'not authenticated' using errcode = '42501';
  end if;

  if p_push_token is not null then
    update public.devices
       set push_token = null, push_token_updated_at = now()
     where push_token = p_push_token
       and not (user_id = v_uid and installation_id = p_installation_id);
  end if;

  insert into public.devices as d
    (user_id, installation_id, platform, device_name, push_token,
     push_token_updated_at, app_version, os_version, last_active_at)
  values
    (v_uid, p_installation_id, p_platform, p_device_name, p_push_token,
     case when p_push_token is not null then now() end, p_app_version, p_os_version, now())
  on conflict (user_id, installation_id) do update
    set platform              = excluded.platform,
        device_name           = coalesce(excluded.device_name, d.device_name),
        push_token            = excluded.push_token,
        push_token_updated_at = case when d.push_token is distinct from excluded.push_token
                                     then now() else d.push_token_updated_at end,
        app_version           = coalesce(excluded.app_version, d.app_version),
        os_version            = coalesce(excluded.os_version, d.os_version),
        last_active_at        = now()
  returning * into v_row;

  return v_row;
end;
$$;

-- =====================================================================
-- 4. notifications – Hộp thư thông báo trong app (theo user)
-- 5. notification_deliveries – Từng lần đẩy tới từng thiết bị (Expo)
-- =====================================================================
create table public.notifications (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles (id) on delete cascade,
  category    varchar(30)  not null default 'system',
  title       varchar(255) not null,
  body        text,
  data        jsonb        not null default '{}'::jsonb,   -- deep link: {"conversation_id": "..."}
  read_at     timestamptz,
  created_at  timestamptz  not null default now(),

  constraint notifications_category_chk check (category in ('chat', 'task', 'system')),
  constraint notifications_data_chk     check (jsonb_typeof(data) = 'object')
);

create index idx_notifications_user_created
  on public.notifications (user_id, created_at desc);

create index idx_notifications_user_unread
  on public.notifications (user_id)
  where read_at is null;

create table public.notification_deliveries (
  id               uuid primary key default gen_random_uuid(),
  notification_id  uuid not null references public.notifications (id) on delete cascade,
  device_id        uuid references public.devices (id) on delete set null,
  push_token       text not null,                 -- token tại thời điểm gửi
  status           varchar(20) not null default 'queued',
  expo_ticket_id   varchar(100),
  error_code       varchar(100),                  -- vd DeviceNotRegistered -> xóa push_token
  error_message    text,
  created_at       timestamptz not null default now(),
  sent_at          timestamptz,
  checked_at       timestamptz,                   -- lúc đọc push receipt

  constraint notification_deliveries_status_chk
    check (status in ('queued', 'sent', 'delivered', 'failed'))
);

create index idx_deliveries_notification on public.notification_deliveries (notification_id);
create index idx_deliveries_device       on public.notification_deliveries (device_id);
-- job đọc push receipt của Expo
create index idx_deliveries_pending_receipt
  on public.notification_deliveries (sent_at)
  where status = 'sent' and expo_ticket_id is not null;

-- =====================================================================
-- 6. goclaw_workspaces – Nhiều GoClaw workspace / server
-- =====================================================================
create table public.goclaw_workspaces (
  id                 uuid primary key default gen_random_uuid(),
  name               varchar(150) not null,
  base_url           text not null,
  api_key_secret_id  uuid,               -- id trong vault.secrets, KHÔNG lưu key ở đây
  is_active          boolean not null default true,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),

  constraint goclaw_workspaces_name_key unique (name)
);

create trigger trg_goclaw_workspaces_updated_at
  before update on public.goclaw_workspaces
  for each row execute function public.set_updated_at();

-- =====================================================================
-- 7. agents – AI Agent
-- =====================================================================
create table public.agents (
  id               uuid primary key default gen_random_uuid(),
  workspace_id     uuid not null references public.goclaw_workspaces (id) on delete restrict,
  name             varchar(150) not null,
  goclaw_agent_id  varchar(150) not null,
  description      text,
  avatar_url       text,
  visibility       varchar(20) not null default 'public',   -- restricted = cần user_agent_access
  is_active        boolean not null default true,
  sort_order       integer not null default 0,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),

  constraint agents_workspace_goclaw_key unique (workspace_id, goclaw_agent_id),
  constraint agents_visibility_chk       check (visibility in ('public', 'restricted'))
);

create index idx_agents_active_sort
  on public.agents (sort_order, name)
  where is_active;

create trigger trg_agents_updated_at
  before update on public.agents
  for each row execute function public.set_updated_at();

-- =====================================================================
-- 8. user_agent_access – Cấp quyền agent 'restricted' cho user
-- =====================================================================
create table public.user_agent_access (
  user_id     uuid not null references public.profiles (id) on delete cascade,
  agent_id    uuid not null references public.agents (id) on delete cascade,
  granted_at  timestamptz not null default now(),
  expires_at  timestamptz,
  primary key (user_id, agent_id)
);

create index idx_user_agent_access_agent on public.user_agent_access (agent_id);

create or replace function public.can_use_agent(p_user_id uuid, p_agent_id uuid)
returns boolean
language sql
stable
set search_path = ''
as $$
  select exists (
    select 1
      from public.agents a
      join public.goclaw_workspaces w on w.id = a.workspace_id
     where a.id = p_agent_id
       and a.is_active
       and w.is_active
       and (
         a.visibility = 'public'
         or exists (
           select 1 from public.user_agent_access x
            where x.user_id = p_user_id
              and x.agent_id = a.id
              and (x.expires_at is null or x.expires_at > now())
         )
       )
  );
$$;

-- Chặn ngay trong DB: không tạo conversation / task với agent chưa được cấp quyền
create or replace function public.enforce_agent_access()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.agent_id is not null and not public.can_use_agent(new.user_id, new.agent_id) then
    raise exception 'agent % is not available for user %', new.agent_id, new.user_id
      using errcode = '42501';
  end if;
  return new;
end;
$$;

-- =====================================================================
-- 9. conversations – Các cuộc trò chuyện độc lập
-- =====================================================================
create table public.conversations (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references public.profiles (id) on delete cascade,
  agent_id           uuid not null references public.agents (id) on delete restrict,
  title              varchar(255),
  title_source       varchar(10) not null default 'auto',   -- auto: AI được đổi tên; user: giữ nguyên
  goclaw_session_id  varchar(255),                          -- NULL tới khi GoClaw trả về
  status             varchar(20) not null default 'active',
  message_count      integer     not null default 0,
  last_message_at    timestamptz,
  pinned_at          timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  archived_at        timestamptz,
  deleted_at         timestamptz,                           -- xóa mềm; job purge xóa hẳn sau N ngày

  constraint conversations_id_user_key    unique (id, user_id),
  constraint conversations_title_src_chk  check (title_source in ('auto', 'user')),
  constraint conversations_status_chk     check (status in ('active', 'archived', 'deleted')),
  constraint conversations_msg_count_chk  check (message_count >= 0),
  constraint conversations_archived_chk   check (status <> 'archived' or archived_at is not null),
  constraint conversations_deleted_chk    check ((status = 'deleted') = (deleted_at is not null))
);

-- Danh sách chat: ghim lên đầu, rồi theo hoạt động gần nhất
create index idx_conversations_user_list
  on public.conversations (user_id, pinned_at desc nulls last, (coalesce(last_message_at, created_at)) desc, id)
  where deleted_at is null;

create index idx_conversations_user_status on public.conversations (user_id, status);
create index idx_conversations_agent       on public.conversations (agent_id);
create index idx_conversations_purge       on public.conversations (deleted_at) where deleted_at is not null;

-- Một GoClaw session (của một agent) không gắn vào hai conversation
create unique index uq_conversations_agent_session
  on public.conversations (agent_id, goclaw_session_id)
  where goclaw_session_id is not null;

create trigger trg_conversations_updated_at
  before update on public.conversations
  for each row execute function public.set_updated_at();

create trigger trg_conversations_agent_access
  before insert or update of agent_id on public.conversations
  for each row execute function public.enforce_agent_access();

-- =====================================================================
-- 10. messages – Lịch sử tin nhắn
-- =====================================================================
create table public.messages (
  id                   uuid primary key default gen_random_uuid(),
  seq                  bigint generated always as identity,   -- thứ tự tuyệt đối, dùng cho cursor
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
  model                varchar(100),
  input_tokens         integer,
  output_tokens        integer,
  cost_usd             numeric(12, 6),
  metadata             jsonb not null default '{}'::jsonb,
  favorited_at         timestamptz,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),

  constraint messages_seq_key             unique (seq),
  constraint messages_id_conversation_key unique (id, conversation_id),
  constraint messages_id_user_key         unique (id, user_id),

  -- message.user_id BẮT BUỘC trùng chủ sở hữu conversation
  constraint messages_conversation_owner_fk
    foreign key (conversation_id, user_id)
    references public.conversations (id, user_id)
    on delete cascade,

  -- chỉ reply tin trong CÙNG conversation
  constraint messages_reply_to_fk
    foreign key (reply_to_message_id, conversation_id)
    references public.messages (id, conversation_id)
    on delete set null (reply_to_message_id),

  constraint messages_role_chk          check (role in ('user', 'assistant', 'system', 'tool')),
  constraint messages_content_type_chk  check (content_type in ('text', 'image', 'file', 'audio', 'video')),
  constraint messages_status_chk        check (status in ('pending', 'processing', 'completed', 'failed', 'cancelled')),
  constraint messages_usage_chk         check (coalesce(input_tokens, 0) >= 0
                                               and coalesce(output_tokens, 0) >= 0
                                               and coalesce(cost_usd, 0) >= 0),
  constraint messages_metadata_chk      check (jsonb_typeof(metadata) = 'object')
);

-- cursor pagination: WHERE conversation_id = $1 AND seq < $cursor ORDER BY seq DESC LIMIT 30
create index idx_messages_conversation_seq on public.messages (conversation_id, seq);
create index idx_messages_user_created     on public.messages (user_id, created_at desc);

create unique index idx_messages_idempotency
  on public.messages (user_id, idempotency_key)
  where idempotency_key is not null;

-- Mỗi conversation chỉ một câu trả lời AI đang chạy -> chặn gửi chồng vào cùng GoClaw session
create unique index uq_messages_one_inflight_reply
  on public.messages (conversation_id)
  where role = 'assistant' and status in ('pending', 'processing');

create index idx_messages_goclaw_message
  on public.messages (conversation_id, goclaw_message_id)
  where goclaw_message_id is not null;

create index idx_messages_reply_to
  on public.messages (reply_to_message_id)
  where reply_to_message_id is not null;

create index idx_messages_user_favorited
  on public.messages (user_id, favorited_at desc)
  where favorited_at is not null;

-- Tìm kiếm không dấu: f_unaccent(content) LIKE '%xin chao%'
create index idx_messages_content_search
  on public.messages using gin (public.f_unaccent(content) extensions.gin_trgm_ops);

create trigger trg_messages_updated_at
  before update on public.messages
  for each row execute function public.set_updated_at();

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

create trigger trg_messages_sync_conversation
  after insert or delete on public.messages
  for each row execute function public.sync_conversation_message_stats();

-- Tìm kiếm lịch sử chat (gọi được từ mobile qua RPC, RLS tự lọc theo user)
create or replace function public.search_messages(
  p_query   text,
  p_limit   integer default 30,
  p_user_id uuid    default null     -- backend (service role) truyền user_id; mobile bỏ trống
)
returns table (
  message_id          uuid,
  conversation_id     uuid,
  conversation_title  varchar,
  role                varchar,
  content             text,
  created_at          timestamptz
)
language sql
stable
set search_path = ''
as $$
  select m.id, m.conversation_id, c.title, m.role, m.content, m.created_at
    from public.messages m
    join public.conversations c on c.id = m.conversation_id
   where m.user_id = coalesce(p_user_id, (select auth.uid()))
     and c.deleted_at is null
     and public.f_unaccent(m.content) like
         '%' || replace(replace(replace(public.f_unaccent(p_query), '\', '\\'), '%', '\%'), '_', '\_') || '%'
   order by m.seq desc
   limit least(greatest(p_limit, 1), 100);
$$;

-- Thống kê token & chi phí theo ngày (giờ VN). security_invoker -> tuân theo RLS của messages
create view public.v_usage_daily
with (security_invoker = true)
as
select m.user_id,
       (m.created_at at time zone 'Asia/Ho_Chi_Minh')::date as usage_date,
       m.model,
       count(*)                          as reply_count,
       coalesce(sum(m.input_tokens), 0)  as input_tokens,
       coalesce(sum(m.output_tokens), 0) as output_tokens,
       coalesce(sum(m.cost_usd), 0)      as cost_usd
  from public.messages m
 where m.role = 'assistant'
 group by 1, 2, 3;

-- =====================================================================
-- 11. message_attachments – File đính kèm
-- Luồng: backend tạo dòng (pending_upload) + signed upload URL -> mobile
-- upload thẳng lên Storage -> backend xác nhận (uploaded) -> gửi tin
-- kèm attachment_ids (attached). File mồ côi > 24h bị job dọn.
-- =====================================================================
create table public.message_attachments (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles (id) on delete cascade,
  message_id  uuid,
  file_name   varchar(255) not null,
  file_path   text not null,          -- chat-attachments/{user_id}/{attachment_id}/{file_name}
  mime_type   varchar(100) not null,
  file_size   bigint not null,
  status      varchar(20) not null default 'pending_upload',
  metadata    jsonb not null default '{}'::jsonb,   -- width, height, duration_ms, ...
  created_at  timestamptz not null default now(),
  attached_at timestamptz,

  constraint message_attachments_file_path_key unique (file_path),
  constraint message_attachments_message_fk
    foreign key (message_id, user_id)
    references public.messages (id, user_id)
    on delete cascade,
  constraint message_attachments_path_chk     check (file_path like user_id::text || '/%'),
  constraint message_attachments_size_chk     check (file_size >= 0),
  constraint message_attachments_status_chk   check (status in ('pending_upload', 'uploaded', 'attached')),
  constraint message_attachments_attached_chk check ((status = 'attached') = (message_id is not null)),
  constraint message_attachments_metadata_chk check (jsonb_typeof(metadata) = 'object')
);

create index idx_attachments_message on public.message_attachments (message_id) where message_id is not null;
create index idx_attachments_orphans on public.message_attachments (created_at) where status <> 'attached';

-- =====================================================================
-- 12. social_accounts – Tài khoản mạng xã hội để đăng bài
-- =====================================================================
create table public.social_accounts (
  id                       uuid primary key default gen_random_uuid(),
  user_id                  uuid not null references public.profiles (id) on delete cascade,
  platform                 varchar(30)  not null,
  external_account_id      varchar(255) not null,   -- page id, channel id, ...
  display_name             varchar(255),
  avatar_url               text,
  access_token_secret_id   uuid,                    -- vault.secrets.id
  refresh_token_secret_id  uuid,                    -- vault.secrets.id
  token_expires_at         timestamptz,
  scopes                   text[] not null default '{}',
  status                   varchar(20) not null default 'active',
  last_error               text,
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),

  constraint social_accounts_id_user_key  unique (id, user_id),
  constraint social_accounts_external_key unique (user_id, platform, external_account_id),
  constraint social_accounts_platform_chk check (platform in ('facebook', 'instagram', 'threads', 'tiktok',
                                                              'youtube', 'x', 'linkedin', 'zalo')),
  constraint social_accounts_status_chk   check (status in ('active', 'expired', 'revoked', 'error'))
);

create index idx_social_accounts_expiring
  on public.social_accounts (token_expires_at)
  where status = 'active' and token_expires_at is not null;

create trigger trg_social_accounts_updated_at
  before update on public.social_accounts
  for each row execute function public.set_updated_at();

-- =====================================================================
-- 13. scheduled_tasks – ĐỊNH NGHĨA lịch hẹn (một lần hoặc lặp lại)
-- Đăng một bài lên nhiều nền tảng = nhiều task cùng group_id
-- (mỗi task một social_account, retry/kết quả độc lập).
-- =====================================================================
create table public.scheduled_tasks (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references public.profiles (id) on delete cascade,
  conversation_id    uuid,
  agent_id           uuid references public.agents (id) on delete set null,
  social_account_id  uuid,
  group_id           uuid,
  task_name          varchar(255) not null,
  task_type          varchar(50)  not null,
  payload            jsonb        not null,
  scheduled_at       timestamptz  not null,        -- lần chạy đầu tiên
  timezone           varchar(100) not null default 'Asia/Ho_Chi_Minh',
  recurrence_rule    text,                         -- RRULE (RFC 5545), NULL = chạy một lần
  ends_at            timestamptz,
  next_run_at        timestamptz,                  -- lần kế tiếp cần tạo run; NULL = hết lịch
  status             varchar(20)  not null default 'active',
  max_attempts       integer      not null default 3,
  run_count          integer      not null default 0,
  last_run_at        timestamptz,
  created_at         timestamptz  not null default now(),
  updated_at         timestamptz  not null default now(),

  constraint scheduled_tasks_id_user_key unique (id, user_id),

  constraint scheduled_tasks_conversation_owner_fk
    foreign key (conversation_id, user_id)
    references public.conversations (id, user_id)
    on delete set null (conversation_id),

  constraint scheduled_tasks_social_owner_fk
    foreign key (social_account_id, user_id)
    references public.social_accounts (id, user_id)
    on delete set null (social_account_id),

  constraint scheduled_tasks_type_chk     check (task_type in ('send_message', 'execute_agent', 'execute_workflow', 'publish_post')),
  -- finished = đã tạo hết các lần chạy (kết quả từng lần xem ở scheduled_task_runs)
  constraint scheduled_tasks_status_chk   check (status in ('active', 'paused', 'finished', 'cancelled')),
  constraint scheduled_tasks_attempts_chk check (max_attempts between 1 and 10),
  constraint scheduled_tasks_payload_chk  check (jsonb_typeof(payload) = 'object'),
  constraint scheduled_tasks_ends_chk     check (ends_at is null or ends_at >= scheduled_at)
);

create index idx_scheduled_tasks_due
  on public.scheduled_tasks (next_run_at)
  where status = 'active' and next_run_at is not null;

create index idx_scheduled_tasks_user         on public.scheduled_tasks (user_id, scheduled_at desc);
create index idx_scheduled_tasks_group        on public.scheduled_tasks (group_id) where group_id is not null;
create index idx_scheduled_tasks_conversation on public.scheduled_tasks (conversation_id) where conversation_id is not null;
create index idx_scheduled_tasks_social       on public.scheduled_tasks (social_account_id) where social_account_id is not null;

create or replace function public.scheduled_tasks_set_defaults()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' and new.status = 'active' and new.next_run_at is null then
    new.next_run_at := new.scheduled_at;
  end if;
  return new;
end;
$$;

create trigger trg_scheduled_tasks_defaults
  before insert on public.scheduled_tasks
  for each row execute function public.scheduled_tasks_set_defaults();

create trigger trg_scheduled_tasks_timezone
  before insert or update of timezone on public.scheduled_tasks
  for each row execute function public.validate_timezone();

create trigger trg_scheduled_tasks_agent_access
  before insert or update of agent_id on public.scheduled_tasks
  for each row execute function public.enforce_agent_access();

create trigger trg_scheduled_tasks_updated_at
  before update on public.scheduled_tasks
  for each row execute function public.set_updated_at();

-- =====================================================================
-- 14. scheduled_task_runs – TỪNG LẦN CHẠY của một task
-- =====================================================================
create table public.scheduled_task_runs (
  id               uuid primary key default gen_random_uuid(),
  task_id          uuid not null,
  user_id          uuid not null,
  scheduled_for    timestamptz not null,
  status           varchar(20) not null default 'scheduled',
  attempts         integer     not null default 0,
  max_attempts     integer     not null default 3,
  next_retry_at    timestamptz,
  locked_by        varchar(100),
  locked_at        timestamptz,
  -- gửi kèm khi gọi hệ thống ngoài để họ tự chống trùng (nếu hỗ trợ)
  idempotency_key  uuid        not null default gen_random_uuid(),
  external_ref     varchar(255),        -- post id / message id phía ngoài -> có rồi thì KHÔNG đăng lại
  result           jsonb,
  last_error       text,
  started_at       timestamptz,
  finished_at      timestamptz,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),

  constraint scheduled_task_runs_occurrence_key  unique (task_id, scheduled_for),
  constraint scheduled_task_runs_idempotency_key unique (idempotency_key),
  constraint scheduled_task_runs_task_owner_fk
    foreign key (task_id, user_id)
    references public.scheduled_tasks (id, user_id)
    on delete cascade,
  constraint scheduled_task_runs_status_chk   check (status in ('scheduled', 'processing', 'completed', 'failed', 'cancelled', 'retrying')),
  constraint scheduled_task_runs_attempts_chk check (attempts >= 0 and max_attempts >= 1),
  constraint scheduled_task_runs_retry_chk    check (status <> 'retrying' or next_retry_at is not null)
);

create index idx_task_runs_due        on public.scheduled_task_runs (scheduled_for) where status = 'scheduled';
create index idx_task_runs_retry      on public.scheduled_task_runs (next_retry_at) where status = 'retrying';
create index idx_task_runs_processing on public.scheduled_task_runs (locked_at)     where status = 'processing';
create index idx_task_runs_user       on public.scheduled_task_runs (user_id, scheduled_for desc);

create trigger trg_scheduled_task_runs_updated_at
  before update on public.scheduled_task_runs
  for each row execute function public.set_updated_at();

-- Worker bước 1: với mỗi task đến hạn (SELECT ... FOR UPDATE SKIP LOCKED),
-- tính lần kế tiếp từ RRULE ở Python rồi gọi hàm này trong CÙNG transaction.
create or replace function public.enqueue_task_run(
  p_task_id      uuid,
  p_scheduled_for timestamptz,
  p_next_run_at  timestamptz       -- NULL = không còn lần nào
)
returns public.scheduled_task_runs
language plpgsql
set search_path = ''
as $$
declare
  v_run public.scheduled_task_runs;
begin
  insert into public.scheduled_task_runs (task_id, user_id, scheduled_for, max_attempts)
  select t.id, t.user_id, p_scheduled_for, t.max_attempts
    from public.scheduled_tasks t
   where t.id = p_task_id
  on conflict (task_id, scheduled_for) do nothing
  returning * into v_run;

  update public.scheduled_tasks
     set next_run_at = p_next_run_at,
         last_run_at = p_scheduled_for,
         run_count   = run_count + case when v_run.id is not null then 1 else 0 end,
         status      = case when p_next_run_at is null then 'finished' else status end
   where id = p_task_id;

  return v_run;
end;
$$;

-- Worker bước 2: claim các run đến hạn. SKIP LOCKED -> nhiều worker không lấy trùng.
-- Run kẹt ở 'processing' (worker chết) KHÔNG tự claim lại, phải đối soát
-- (đặc biệt publish_post: kiểm tra external_ref trước khi thử lại).
create or replace function public.claim_due_task_runs(
  p_worker_id text,
  p_limit     integer default 10
)
returns setof public.scheduled_task_runs
language sql
set search_path = ''
as $$
  with due as (
    select r.id
      from public.scheduled_task_runs r
      join public.scheduled_tasks t on t.id = r.task_id
     where ((r.status = 'scheduled' and r.scheduled_for <= now())
         or (r.status = 'retrying'  and r.next_retry_at <= now()))
       and t.status not in ('paused', 'cancelled')
     order by coalesce(r.next_retry_at, r.scheduled_for)
     limit p_limit
     for update of r skip locked
  )
  update public.scheduled_task_runs r
     set status     = 'processing',
         locked_by  = p_worker_id,
         locked_at  = now(),
         attempts   = r.attempts + 1,
         started_at = coalesce(r.started_at, now())
    from due
   where r.id = due.id
  returning r.*;
$$;

-- =====================================================================
-- 15. scheduled_task_logs – Nhật ký từng lần thử của một run
-- =====================================================================
create table public.scheduled_task_logs (
  id                uuid primary key default gen_random_uuid(),
  run_id            uuid not null references public.scheduled_task_runs (id) on delete cascade,
  attempt_number    integer not null,
  status            varchar(20) not null,
  request_payload   jsonb,               -- KHÔNG ghi token/API key vào đây
  response_payload  jsonb,
  error_message     text,
  started_at        timestamptz,
  finished_at       timestamptz,
  created_at        timestamptz not null default now(),

  constraint scheduled_task_logs_attempt_key unique (run_id, attempt_number),
  constraint scheduled_task_logs_attempt_chk check (attempt_number >= 1),
  constraint scheduled_task_logs_status_chk  check (status in ('processing', 'completed', 'failed', 'cancelled'))
);

-- =====================================================================
-- 16. outbox_events – Hàng đợi việc gọi ra ngoài (GoClaw, push, ...)
-- Ghi cùng transaction với dữ liệu chính; worker xử lý và đối soát
-- khi FastAPI mất kết nối giữa chừng.
-- =====================================================================
create table public.outbox_events (
  id              uuid primary key default gen_random_uuid(),
  event_type      varchar(100) not null,   -- vd goclaw.send_message, push.send, storage.purge_user
  aggregate_type  varchar(50)  not null,   -- vd message, conversation, profile
  aggregate_id    uuid         not null,
  payload         jsonb        not null default '{}'::jsonb,
  status          varchar(20)  not null default 'pending',
  attempts        integer      not null default 0,
  available_at    timestamptz  not null default now(),
  locked_by       varchar(100),
  locked_at       timestamptz,
  last_error      text,
  created_at      timestamptz  not null default now(),
  processed_at    timestamptz,

  constraint outbox_events_status_chk  check (status in ('pending', 'processing', 'done', 'failed')),
  constraint outbox_events_payload_chk check (jsonb_typeof(payload) = 'object')
);

create index idx_outbox_pending   on public.outbox_events (available_at) where status = 'pending';
create index idx_outbox_aggregate on public.outbox_events (aggregate_type, aggregate_id);

create or replace function public.claim_outbox_events(
  p_worker_id text,
  p_limit     integer default 20
)
returns setof public.outbox_events
language sql
set search_path = ''
as $$
  with due as (
    select e.id
      from public.outbox_events e
     where e.status = 'pending' and e.available_at <= now()
     order by e.available_at
     limit p_limit
     for update skip locked
  )
  update public.outbox_events e
     set status    = 'processing',
         locked_by = p_worker_id,
         locked_at = now(),
         attempts  = e.attempts + 1
    from due
   where e.id = due.id
  returning e.*;
$$;
