import Apis, { endpoints } from '@/config/Apis';

// Cùng quy tắc với _VN_PHONE ở backend (app/schemas/mobile.py)
const VN_PHONE = /^(?:\+?84|0)0?[35789][0-9]{8}$/;

export const MIN_PASSWORD_LENGTH = 8;

export const isValidPhone = (phone) => VN_PHONE.test(phone.replace(/[\s.\-()]/g, ''));

const toSession = ({ user, access_token, refresh_token }) => ({ ...user, access_token, refresh_token });

export const login = async (phone, password) => {
  const res = await Apis.post(endpoints.login, { phone, password });
  return toSession(res.data);
};

export const register = async (fullName, phone, password) => {
  const res = await Apis.post(endpoints.register, { full_name: fullName, phone, password });
  return toSession(res.data);
};

export const getErrorMessage = (error) => {
  if (!error.response) return 'Không kết nối được máy chủ. Vui lòng thử lại.';
  const { detail } = error.response.data ?? {};
  if (typeof detail === 'string') return detail;
  if (typeof detail?.message === 'string') return detail.message;
  if (error.response.status === 422) return 'Thông tin chưa hợp lệ. Vui lòng kiểm tra lại.';
  return 'Có lỗi xảy ra. Vui lòng thử lại sau.';
};