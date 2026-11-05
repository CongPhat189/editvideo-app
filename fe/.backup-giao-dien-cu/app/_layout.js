import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import { useCallback, useEffect, useReducer, useRef, useState } from 'react';

import { MyUserContext } from '@/config/Contexts';
import { palettes, ThemeContext } from '@/constants/theme';
import { MyUserReducer } from '@/reducers/reducers';
import { getThemePreference, saveThemePreference } from '@/services/appearance';

// Trang mở từ Sidebar không trượt thêm: nội dung tự trượt vào bằng hiệu ứng khép Sidebar
const drawerScreenOptions = ({ route }) => ({
  animation: route.params?.fromDrawer ? 'none' : 'fade',
  gestureEnabled: true,
});

export default function RootLayout() {
  const [user, dispatch] = useReducer(MyUserReducer, null);
  const [theme, setTheme] = useState('dark');
  const themeVersion = useRef(0);
  const token = user?.access_token;
  const colors = palettes[theme];

  useEffect(() => {
    if (!token) {
      setTheme('dark');
      return undefined;
    }
    let active = true;
    const requestedVersion = themeVersion.current;
    getThemePreference(token)
      .then((savedTheme) => {
        if (active && requestedVersion === themeVersion.current) setTheme(savedTheme);
      })
      .catch(() => {});
    return () => { active = false; };
  }, [token]);

  const updateTheme = useCallback((nextTheme) => {
    themeVersion.current += 1;
    setTheme(nextTheme);
    if (token) saveThemePreference(token, nextTheme).catch(() => {});
  }, [token]);

  return (
    <MyUserContext.Provider value={[user, dispatch]}>
      <ThemeContext.Provider value={{ theme, colors, setTheme: updateTheme }}>
        <ThemeProvider value={theme === 'dark' ? DarkTheme : DefaultTheme}>
          <Stack
            screenOptions={{
              headerShown: false,
              animation: 'slide_from_right',
              gestureEnabled: true,
              contentStyle: { backgroundColor: colors.backgroundDeep },
            }}
          >
            <Stack.Protected guard={!!user}>
              <Stack.Screen name="index" options={{ gestureEnabled: false }} />
              <Stack.Screen name="settings" options={{ presentation: 'fullScreenModal' }} />
              <Stack.Screen name="profile" options={{ presentation: 'fullScreenModal' }} />
              <Stack.Screen name="projects/new" options={drawerScreenOptions} />
              <Stack.Screen name="projects/[id]/index" options={drawerScreenOptions} />
              <Stack.Screen name="projects/[id]/schedule" />
              <Stack.Screen name="scheduled" options={drawerScreenOptions} />
              <Stack.Screen name="agents/index" options={drawerScreenOptions} />
              <Stack.Screen name="agents/new" />
            </Stack.Protected>
            <Stack.Protected guard={!user}>
              <Stack.Screen name="login" />
              <Stack.Screen name="register" />
            </Stack.Protected>
          </Stack>
        </ThemeProvider>
      </ThemeContext.Provider>
    </MyUserContext.Provider>
  );
}
