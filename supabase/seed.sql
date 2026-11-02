-- =====================================================================
-- Seed: GoClaw workspace + Agents
-- Trước khi chạy trên production, thay:
--   * base_url  -> địa chỉ GoClaw server của bạn
--   * goclaw_agent_id -> ID agent thật trên GoClaw
-- API key GoClaw lưu vào Vault rồi gắn id vào workspace (xem docs/SUPABASE_SETUP.md).
-- Chạy lại nhiều lần an toàn (upsert).
-- =====================================================================

insert into public.goclaw_workspaces (name, base_url)
values ('default', 'https://REPLACE_ME.goclaw.local')
on conflict (name) do update
  set base_url = excluded.base_url;

insert into public.agents (workspace_id, name, goclaw_agent_id, description, visibility, is_active, sort_order)
select w.id, a.name, a.goclaw_agent_id, a.description, a.visibility, true, a.sort_order
  from public.goclaw_workspaces w
 cross join (values
   ('Trợ lý chung',   'REPLACE_ME_general_assistant', 'Trò chuyện, hỏi đáp và hỗ trợ công việc hằng ngày.', 'public',     10),
   ('Content Writer', 'REPLACE_ME_content_writer',    'Viết bài, caption và lên lịch đăng bài mạng xã hội.', 'public',     20),
   ('Video Editor',   'REPLACE_ME_video_editor',      'Hỗ trợ lên kịch bản và dựng video ngắn.',             'restricted', 30)
 ) as a (name, goclaw_agent_id, description, visibility, sort_order)
 where w.name = 'default'
on conflict (workspace_id, goclaw_agent_id) do update
  set name        = excluded.name,
      description = excluded.description,
      visibility  = excluded.visibility,
      is_active   = excluded.is_active,
      sort_order  = excluded.sort_order;
