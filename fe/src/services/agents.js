import { authApis, endpoints } from '@/config/Apis';

// GET /agents chỉ trả id và name, không có khóa bí mật
export const getAgents = async (token) => {
  const res = await authApis(token).get(endpoints.agents);
  return res.data;
};

export const testAgentConnection = async (token, { domain, apiKey, agentKey }) => {
  const res = await authApis(token).post(endpoints.agentTestConnection, {
    domain,
    api_key: apiKey,
    agent_key: agentKey,
  });
  return res.data;
};

export const createAgent = async (token, { name, domain, apiKey, agentKey }) => {
  const res = await authApis(token).post(endpoints.agents, {
    name,
    domain,
    api_key: apiKey,
    agent_key: agentKey,
  });
  return res.data;
};
