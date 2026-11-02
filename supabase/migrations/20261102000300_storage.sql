-- =====================================================================
-- Supabase Storage: buckets + policies
--
--   avatars/           {user_id}/{uuid}.jpg                    public
--   chat-attachments/  {user_id}/{attachment_id}/{file_name}   private
--   scheduled-media/   {user_id}/{task_id}/{file_name}         private
--
-- * avatars: mobile tự upload vào thư mục của mình (tên file mới mỗi lần
--   đổi ảnh để không dính cache), rồi update profiles.avatar_path.
-- * chat-attachments, scheduled-media: backend tạo signed upload URL,
--   mobile upload thẳng lên Storage (không đi vòng qua FastAPI); đọc bằng
--   signed URL hoặc trực tiếp nhờ policy SELECT bên dưới.
-- * Free plan giới hạn mỗi file tối đa 50 MB.
-- =====================================================================

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('avatars', 'avatars', true, 5242880,                       -- 5 MB
   array['image/jpeg', 'image/png', 'image/webp', 'image/heic']),

  ('chat-attachments', 'chat-attachments', false, 52428800,   -- 50 MB
   array['image/*', 'video/*', 'audio/*',
         'application/pdf', 'text/plain', 'text/csv',
         'application/msword',
         'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
         'application/vnd.ms-excel',
         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
         'application/vnd.openxmlformats-officedocument.presentationml.presentation']),

  ('scheduled-media', 'scheduled-media', false, 52428800,     -- 50 MB
   array['image/*', 'video/*'])
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- avatars: user quản lý file trong thư mục {user_id}/ của mình
create policy "avatars_select_own"
  on storage.objects for select to authenticated
  using (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text);

create policy "avatars_insert_own"
  on storage.objects for insert to authenticated
  with check (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text);

create policy "avatars_update_own"
  on storage.objects for update to authenticated
  using      (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text);

create policy "avatars_delete_own"
  on storage.objects for delete to authenticated
  using (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text);

-- File riêng tư: chỉ đọc file trong thư mục của mình
create policy "chat_attachments_select_own"
  on storage.objects for select to authenticated
  using (bucket_id = 'chat-attachments' and (storage.foldername(name))[1] = (select auth.uid())::text);

create policy "scheduled_media_select_own"
  on storage.objects for select to authenticated
  using (bucket_id = 'scheduled-media' and (storage.foldername(name))[1] = (select auth.uid())::text);
