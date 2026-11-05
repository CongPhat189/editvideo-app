import { createContext, useContext, useMemo } from 'react';
import { Platform } from 'react-native';

// Bảng màu "Noir & Champagne": nền đen ánh than, điểm nhấn vàng champagne.
// Bản sáng là nền ngà (ivory) với vàng đồng đậm hơn để đủ tương phản.
export const palettes = {
  dark: {
    background: '#0E0E10',
    backgroundDeep: '#08080A',
    surface: '#17171A',
    surfaceRaised: '#1F1F23',
    card: '#131315',
    primary: '#D9BC85',
    onPrimary: '#1A1408',
    text: '#F5F1E8',
    textSecondary: '#A9A49A',
    textMuted: '#77736B',
    divider: '#26252A',
    border: 'rgba(255, 255, 255, 0.07)',
    borderStrong: 'rgba(255, 255, 255, 0.12)',
    error: '#F08A80',
    success: '#7FD1A8',
    successSoft: 'rgba(127, 209, 168, 0.08)',
    successBorder: 'rgba(127, 209, 168, 0.24)',
    errorSoft: 'rgba(240, 138, 128, 0.08)',
    errorBorder: 'rgba(240, 138, 128, 0.24)',
    overlay: 'rgba(0, 0, 0, 0.55)',
    accent: '#D9BC85',
    avatar: '#2A2316',
    onAvatar: '#E9D2A4',
    gold: '#D9BC85',
    goldLight: '#F3E2BC',
    goldDeep: '#A8864E',
    goldSoft: 'rgba(217, 188, 133, 0.09)',
    goldBorder: 'rgba(217, 188, 133, 0.30)',
    glow: '#C9A15F',
    shadow: '#000000',
    statusBar: 'light',
  },
  light: {
    background: '#F6F2EA',
    backgroundDeep: '#FBF9F4',
    surface: '#EDE7DB',
    surfaceRaised: '#F2EDE3',
    card: '#FFFFFF',
    primary: '#A9843F',
    onPrimary: '#FFFFFF',
    text: '#1B1813',
    textSecondary: '#5F584C',
    textMuted: '#8D8576',
    divider: '#E1D9CA',
    border: 'rgba(60, 45, 20, 0.09)',
    borderStrong: 'rgba(60, 45, 20, 0.16)',
    error: '#B4372B',
    success: '#2F7D57',
    successSoft: 'rgba(47, 125, 87, 0.07)',
    successBorder: 'rgba(47, 125, 87, 0.22)',
    errorSoft: 'rgba(180, 55, 43, 0.06)',
    errorBorder: 'rgba(180, 55, 43, 0.2)',
    overlay: 'rgba(27, 24, 19, 0.35)',
    accent: '#A9843F',
    avatar: '#F1E5CB',
    onAvatar: '#7A5A22',
    gold: '#A9843F',
    goldLight: '#C9A866',
    goldDeep: '#8A6A2E',
    goldSoft: 'rgba(169, 132, 63, 0.08)',
    goldBorder: 'rgba(169, 132, 63, 0.32)',
    glow: '#E2C68E',
    shadow: '#5A4320',
    statusBar: 'dark',
  },
};

// Chữ có chân cho tiêu đề lớn tạo cảm giác sang trọng; nội dung vẫn dùng font hệ thống để dễ đọc
export const fonts = {
  display: Platform.select({ ios: 'Georgia', android: 'serif', default: 'Georgia, "Times New Roman", serif' }),
  mono: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'ui-monospace, Menlo, monospace' }),
};

export const ThemeContext = createContext({
  theme: 'dark',
  colors: palettes.dark,
  setTheme: () => {},
});

export const useAppTheme = () => useContext(ThemeContext);
export const useThemeColors = () => useAppTheme().colors;

export const useThemeStyles = (createStyles) => {
  const { colors } = useAppTheme();
  return useMemo(() => createStyles(colors), [colors, createStyles]);
};
