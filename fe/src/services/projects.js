import { authApis, endpoints } from '@/config/Apis';

// Dự án chính là một cuộc trò chuyện (bảng conversations): có id riêng và lịch sử chat riêng
const PAGE_SIZE = 100;
const MESSAGE_PAGE_SIZE = 30;
const MAX_RECENT = 20;
const RECENT_KEY = 'recent_projects';

export const getProjects = async (token) => {
  const res = await authApis(token).get(endpoints.conversations, { params: { limit: PAGE_SIZE } });
  return res.data;
};

export const getProject = async (token, id) => {
  const res = await authApis(token).get(endpoints.conversation(id));
  return res.data;
};

export const createProject = async (token, name, agentId) => {
  const res = await authApis(token).post(endpoints.conversations, { title: name, agent_id: agentId });
  return res.data;
};

export const getMessages = async (token, id, before) => {
  const res = await authApis(token).get(endpoints.messages(id), {
    params: { limit: MESSAGE_PAGE_SIZE, ...(before ? { before } : {}) },
  });
  return res.data;
};

export const sendMessage = async (token, id, content) => {
  const res = await authApis(token).post(endpoints.messages(id), { content });
  return res.data;
};

export const sendMessageWithFiles = async (token, id, content, files) => {
  const form = new FormData();
  files.forEach((file) => {
    form.append('files', { uri: file.uri, name: file.fileName, type: file.mimeType });
  });
  if (content) form.append('content', content);
  const res = await authApis(token).post(endpoints.messagesUpload(id), form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    transformRequest: (data) => data,
  });
  return res.data;
};

const getSettingsJson = async (token) => {
  const res = await authApis(token).get(endpoints.me);
  return res.data.settings?.settings_json ?? {};
};

// Lưu trong user_settings.settings_json nên còn nguyên khi tải lại trang hoặc đổi thiết bị
export const getRecentProjectIds = async (token) => {
  const settings = await getSettingsJson(token);
  return (settings[RECENT_KEY] ?? []).map((item) => item.id);
};

export const markProjectOpened = async (token, id) => {
  // PATCH /me/settings ghi đè cả settings_json nên phải giữ lại các khóa khác
  const settings = await getSettingsJson(token);
  const others = (settings[RECENT_KEY] ?? []).filter((item) => item.id !== id);
  const recent = [{ id, opened_at: new Date().toISOString() }, ...others].slice(0, MAX_RECENT);
  await authApis(token).patch(endpoints.settings, {
    settings_json: { ...settings, [RECENT_KEY]: recent },
  });
};
