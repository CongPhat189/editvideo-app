-- =====================================================================
-- Row Level Security, quyền truy cập, Realtime
--
-- Ai được làm gì:
--   * anon (chưa đăng nhập): không đọc/ghi gì trong public.
--   * authenticated (mobile, JWT Supabase Auth):
--       - ĐỌC dữ liệu của chính mình (để hiển thị + nghe Realtime).
--       - GHI trực tiếp chỉ: profiles (tên, avatar), user_settings,
--         notifications.read_at, thiết bị qua RPC register_device().
--   * FastAPI (service_role / user postgres, bypass RLS): mọi thao tác
--     còn lại – chat, GoClaw, lịch hẹn, upload. Backend PHẢI tự lọc
--     theo user_id lấy từ JWT đã verify.
-- =====================================================================

alter table public.profiles                enable row level security;
alter table public.user_settings           enable row level security;
alter table public.devices                 enable row level security;
alter table public.notifications           enable row level security;
alter table public.notification_deliveries enable row level security;
alter table public.goclaw_workspaces       enable row level security;
alter table public.agents                  enable row level security;
alter table public.user_agent_access       enable row level security;
alter table public.conversations           enable row level security;
alter table public.messages                enable row level security;
alter table public.message_attachments     enable row level security;
alter table public.social_accounts         enable row level security;
alter table public.scheduled_tasks         enable row level security;
alter table public.scheduled_task_runs     enable row level security;
alter table public.scheduled_task_logs     enable row level security;
alter table public.outbox_events           enable row level security;

-- Supabase mặc định GRANT ALL cho anon/authenticated. Thu hồi hết rồi cấp lại tối thiểu.
revoke all on all tables    in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke all on all functions in schema public from public, anon, authenticated;

-- ---------------------------------------------------------------------
-- Grants cho authenticated
-- ---------------------------------------------------------------------
grant select (id, full_name, avatar_path, status, deletion_requested_at, created_at, updated_at)
  on public.profiles to authenticated;
grant update (full_name, avatar_path) on public.profiles to authenticated;

grant select on public.user_settings to authenticated;
grant update (theme, language, timezone, notification_enabled, settings_json)
  on public.user_settings to authenticated;

grant select on public.devices to authenticated;

grant select on public.notifications to authenticated;
grant update (read_at) on public.notifications to authenticated;

-- agents: ẩn workspace_id, goclaw_agent_id
grant select (id, name, description, avatar_url, visibility, is_active, sort_order)
  on public.agents to authenticated;

grant select on public.user_agent_access   to authenticated;
grant select on public.conversations       to authenticated;
grant select on public.messages            to authenticated;
grant select on public.message_attachments to authenticated;
grant select on public.v_usage_daily       to authenticated;

-- social_accounts: ẩn id của secret trong Vault
grant select (id, user_id, platform, external_account_id, display_name, avatar_url,
              token_expires_at, scopes, status, last_error, created_at, updated_at)
  on public.social_accounts to authenticated;

grant select on public.scheduled_tasks     to authenticated;
grant select on public.scheduled_task_runs to authenticated;
grant select on public.scheduled_task_logs to authenticated;

-- Không grant: goclaw_workspaces, notification_deliveries, outbox_events

-- RPC mobile được gọi (f_unaccent cần cho search_messages)
grant execute on function public.register_device(text, text, text, text, text, text) to authenticated;
grant execute on function public.search_messages(text, integer, uuid)                to authenticated;
grant execute on function public.f_unaccent(text)                                    to authenticated;

-- ---------------------------------------------------------------------
-- Policies. (select auth.uid()) để Postgres tính một lần mỗi câu lệnh.
-- ---------------------------------------------------------------------
create policy profiles_select_own on public.profiles
  for select to authenticated
  using (id = (select auth.uid()));

create policy profiles_update_own on public.profiles
  for update to authenticated
  using (id = (select auth.uid()))
  with check (id = (select auth.uid()));

create policy user_settings_select_own on public.user_settings
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy user_settings_update_own on public.user_settings
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create policy devices_select_own on public.devices
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy notifications_select_own on public.notifications
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy notifications_update_own on public.notifications
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- Chỉ thấy agent public hoặc agent đã được cấp quyền (còn hạn)
create policy agents_select_allowed on public.agents
  for select to authenticated
  using (
    is_active
    and (
      visibility = 'public'
      or exists (
        select 1 from public.user_agent_access x
         where x.agent_id = agents.id
           and x.user_id = (select auth.uid())
           and (x.expires_at is null or x.expires_at > now())
      )
    )
  );

create policy user_agent_access_select_own on public.user_agent_access
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy conversations_select_own on public.conversations
  for select to authenticated
  using (user_id = (select auth.uid()) and deleted_at is null);

create policy messages_select_own on public.messages
  for select to authenticated
  using (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.conversations c
       where c.id = messages.conversation_id
         and c.deleted_at is null
    )
  );

create policy message_attachments_select_own on public.message_attachments
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy social_accounts_select_own on public.social_accounts
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy scheduled_tasks_select_own on public.scheduled_tasks
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy scheduled_task_runs_select_own on public.scheduled_task_runs
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy scheduled_task_logs_select_own on public.scheduled_task_logs
  for select to authenticated
  using (
    exists (
      select 1 from public.scheduled_task_runs r
       where r.id = scheduled_task_logs.run_id
         and r.user_id = (select auth.uid())
    )
  );

-- ---------------------------------------------------------------------
-- Realtime: mobile nghe thay đổi để đồng bộ nhiều thiết bị
-- (Realtime tôn trọng RLS ở trên nên mỗi user chỉ nhận dữ liệu của mình)
-- ---------------------------------------------------------------------
do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    alter publication supabase_realtime
      add table public.conversations,
                public.messages,
                public.scheduled_task_runs,
                public.notifications;
  end if;
end;
$$;
