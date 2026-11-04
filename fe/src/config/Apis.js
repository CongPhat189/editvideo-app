import axios from "axios";

const BASE_URL = process.env.EXPO_PUBLIC_API_URL || "http://192.168.0.43:8000";

export const endpoints = {
    'login': '/auth/login',
    'register': '/auth/register',
    'me': '/me',
    'settings': '/me/settings',
    'agents': '/agents',
    'agentTestConnection': '/agents/test-connection',
    'conversations': '/conversations',
    'conversation': (id) => `/conversations/${id}`,
    'messages': (id) => `/conversations/${id}/messages`,
    'messagesUpload': (id) => `/conversations/${id}/messages/upload`,
    'schedules': '/schedules'
}

export const authApis = (token) => {
    return axios.create({
        baseURL: BASE_URL,
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
}

export default axios.create({
    baseURL: BASE_URL
})
