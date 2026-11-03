import axios from "axios";

export const endpoints = {
    'login': '/auth/login',
    'register': '/auth/register'
}

export const authApis = (token) => {
    return axios.create({
        baseURL: "http://192.168.0.43:8000",
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
}

export default axios.create({
        baseURL: "http://192.168.0.43:8000",
})