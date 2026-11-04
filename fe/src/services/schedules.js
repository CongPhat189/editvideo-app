import { authApis, endpoints } from '@/config/Apis';

const PAGE_SIZE = 100;
const MAX_PAGES = 5;
// Backend mặc định hiểu giờ nhập theo Asia/Ho_Chi_Minh (UTC+7)
const TIMEZONE_OFFSET_HOURS = 7;
const INPUT_FORMAT = /^(\d{1,2})\/(\d{1,2})\/(\d{4}) (\d{1,2}):(\d{2})$/;

// Đúng danh sách backend nhận (app/schemas/schedule.py)
export const PLATFORMS = ['Facebook', 'YouTube', 'TikTok', 'Instagram', 'Website'];

export const getSchedules = async (token) => {
  const schedules = [];
  for (let page = 0; page < MAX_PAGES; page += 1) {
    const res = await authApis(token).get(endpoints.schedules, {
      params: { limit: PAGE_SIZE, offset: page * PAGE_SIZE },
    });
    schedules.push(...res.data);
    if (res.data.length < PAGE_SIZE) break;
  }
  return schedules;
};

// Không gửi content: backend lưu lịch và báo ngay cho agent "hẹn lịch đăng lên ... vào ..."
export const createSchedule = async (token, { projectId, platforms, time }) => {
  const res = await authApis(token).post(endpoints.schedules, {
    conversation_id: projectId,
    platforms,
    scheduled_at: time,
  });
  return res.data;
};

// Ngày giờ hiện tại theo múi giờ của lịch, không theo múi giờ của máy
export const getScheduleNow = () => {
  const now = new Date(Date.now() + TIMEZONE_OFFSET_HOURS * 3600000);
  return {
    year: now.getUTCFullYear(),
    month: now.getUTCMonth(),
    hour: now.getUTCHours(),
    dayKey: now.toISOString().slice(0, 10),
  };
};

export const validateScheduleTime = (text) => {
  const match = INPUT_FORMAT.exec(text);
  if (!match) return 'Nhập theo dạng 05/11/2026 20:00';
  const [day, month, year, hour, minute] = match.slice(1).map(Number);
  const date = new Date(Date.UTC(year, month - 1, day, hour, minute));
  const isRealDate =
    date.getUTCDate() === day &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCHours() === hour &&
    date.getUTCMinutes() === minute;
  if (!isRealDate) return 'Ngày giờ không hợp lệ';
  if (date.getTime() - TIMEZONE_OFFSET_HOURS * 3600000 <= Date.now()) return 'Thời gian phải ở tương lai';
  return null;
};

// scheduled_at đã ở múi giờ của lịch, đọc thẳng từ chuỗi để không bị đổi theo múi giờ của máy
export const getScheduleDayKey = (schedule) => schedule.scheduled_at.slice(0, 10);

export const formatScheduleTime = (schedule) => {
  const [date, time] = schedule.scheduled_at.split('T');
  const [year, month, day] = date.split('-');
  return `${day}/${month}/${year} ${time.slice(0, 5)}`;
};
