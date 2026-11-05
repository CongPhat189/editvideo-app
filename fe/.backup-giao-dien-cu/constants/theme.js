import { createContext, useContext, useMemo } from 'react';

export const palettes = {
  dark: {
    background: '#232325',
    backgroundDeep: '#000000',
    surface: '#2D2D31',
    surfaceRaised: '#353539',
    primary: '#F4F4F5',
    onPrimary: '#18181B',
    text: '#FFFFFF',
    textSecondary: '#A1A1AA',
    textMuted: '#85858D',
    divider: '#3A3A3E',
    error: '#F87171',
    success: '#34D399',
    successSoft: 'rgba(52, 211, 153, 0.08)',
    successBorder: 'rgba(52, 211, 153, 0.22)',
    errorSoft: 'rgba(248, 113, 113, 0.08)',
    errorBorder: 'rgba(248, 113, 113, 0.22)',
    overlay: 'rgba(0, 0, 0, 0.3)',
    accent: '#2563EB',
    avatar: '#10A37F',
  },
  light: {
    background: '#F7F7F8',
    backgroundDeep: '#FFFFFF',
    surface: '#EEEEF0',
    surfaceRaised: '#F3F3F5',
    primary: '#18181B',
    onPrimary: '#FFFFFF',
    text: '#18181B',
    textSecondary: '#62626A',
    textMuted: '#85858D',
    divider: '#D9D9DE',
    error: '#DC2626',
    success: '#059669',
    successSoft: 'rgba(5, 150, 105, 0.08)',
    successBorder: 'rgba(5, 150, 105, 0.22)',
    errorSoft: 'rgba(220, 38, 38, 0.06)',
    errorBorder: 'rgba(220, 38, 38, 0.2)',
    overlay: 'rgba(0, 0, 0, 0.22)',
    accent: '#2563EB',
    avatar: '#10A37F',
  },
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
