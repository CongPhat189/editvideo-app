import { authApis, endpoints } from '@/config/Apis';

const THEME_KEY = 'color_scheme';

export const getThemePreference = async (token) => {
  const res = await authApis(token).get(endpoints.me);
  const theme = res.data.settings?.settings_json?.[THEME_KEY];
  return theme === 'light' ? 'light' : 'dark';
};

export const saveThemePreference = async (token, theme) => {
  const api = authApis(token);
  const res = await api.get(endpoints.me);
  const settings = res.data.settings?.settings_json ?? {};
  await api.patch(endpoints.settings, {
    settings_json: { ...settings, [THEME_KEY]: theme },
  });
};
