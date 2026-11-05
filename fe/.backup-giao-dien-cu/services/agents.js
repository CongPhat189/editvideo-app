import { authApis, endpoints } from '@/config/Apis';

export const getAgentErrorMessage = (error) => {
  if (!error.response) return 'Không thể kết nối tới máy chủ. Vui lòng kiểm tra mạng hoặc backend.';
  const { detail } = error.response.data ?? {};
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || d.message || JSON.stringify(d)).join('\n');
  }
  if (typeof detail === 'object' && detail !== null) {
    return detail.message || JSON.stringify(detail);
  }
  if (error.response.status === 404) return 'Không tìm thấy Agent.';
  if (error.response.status === 422) return 'Thông tin chưa hợp lệ. Vui lòng kiểm tra lại.';
  return 'Có lỗi xảy ra khi xử lý Agent. Vui lòng thử lại sau.';
};

/**
 * Lấy danh sách rút gọn cho dropdown (chỉ id và name)
 */
export const getAgents = async (token) => {
  const res = await authApis(token).get(endpoints.agents);
  return res.data;
};

/**
 * Lấy danh sách chi tiết Agent thuộc user_id (kèm domain, masked keys)
 */
export const getAgentsByUser = async (token, userId) => {
  const endpoint = userId ? endpoints.agentsByUser(userId) : endpoints.agents;
  const res = await authApis(token).get(endpoint);
  return res.data;
};

/**
 * Xem chi tiết 1 Agent
 */
export const getAgentDetail = async (token, agentId) => {
  const res = await authApis(token).get(endpoints.agentDetail(agentId));
  return res.data;
};

/**
 * Tạo mới Agent
 */
export const createAgent = async (token, { name, domain, apiKey, agentKey }) => {
  const res = await authApis(token).post(endpoints.agents, {
    name: name?.trim(),
    domain: domain?.trim(),
    api_key: apiKey?.trim() || null,
    agent_key: agentKey?.trim() || null,
  });
  return res.data;
};

/**
 * Cập nhật Agent
 */
export const updateAgent = async (token, agentId, { name, domain, apiKey, agentKey }) => {
  const payload = {};
  if (name !== undefined) payload.name = name.trim();
  if (domain !== undefined) payload.domain = domain.trim();
  if (apiKey !== undefined && apiKey !== '') payload.api_key = apiKey.trim();
  if (agentKey !== undefined && agentKey !== '') payload.agent_key = agentKey.trim();

  const res = await authApis(token).put(endpoints.agentUpdate(agentId), payload);
  return res.data;
};

/**
 * Xóa Agent
 */
export const deleteAgent = async (token, agentId) => {
  const res = await authApis(token).delete(endpoints.agentDelete(agentId));
  return res.data;
};

/**
 * Kiểm tra kết nối trực tiếp với domain và key tùy chọn
 */
export const testAgentConnection = async (token, { domain, apiKey, agentKey }) => {
  const res = await authApis(token).post(endpoints.agentTestConnection, {
    domain: domain?.trim(),
    api_key: apiKey?.trim() || null,
    agent_key: agentKey?.trim() || null,
  });
  return res.data;
};

/**
 * Kiểm tra kết nối của Agent đã lưu
 */
export const testSavedAgentConnection = async (token, agentId) => {
  const res = await authApis(token).post(endpoints.agentTestSaved(agentId));
  return res.data;
};
