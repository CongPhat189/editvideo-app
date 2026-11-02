-- =====================================================================
-- Seed: 3 agent mẫu. Chạy lại nhiều lần an toàn.
-- Đổi domain và đặt API key thật bằng lệnh (key được mã hóa trước khi lưu):
--   uv run python manage.py agent "Trợ lý chung" --domain https://goclaw.cua-ban.com --set-key
-- =====================================================================

insert into public.agents (name, domain)
select v.name, 'https://REPLACE_ME.goclaw.local'
  from (values ('Trợ lý chung'), ('Content Writer'), ('Video Editor')) as v (name)
 where not exists (select 1 from public.agents a where a.name = v.name);
