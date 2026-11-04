import { DarkTheme, Stack, ThemeProvider } from 'expo-router';
import { useReducer } from 'react';

import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import { MyUserReducer } from '@/reducers/reducers';

// Trang mở từ Sidebar không trượt thêm: nội dung tự trượt vào bằng hiệu ứng khép Sidebar
const drawerScreenOptions = ({ route }) => ({
  animation: route.params?.fromDrawer ? 'none' : 'fade',
  gestureEnabled: false,
});

export default function RootLayout() {
  const [user, dispatch] = useReducer(MyUserReducer, null);

  return (
    <MyUserContext.Provider value={[user, dispatch]}>
      <ThemeProvider value={DarkTheme}>
        <Stack
          screenOptions={{
            headerShown: false,
            animation: 'slide_from_right',
            contentStyle: { backgroundColor: colors.backgroundDeep },
          }}
        >
          <Stack.Protected guard={!!user}>
            <Stack.Screen name="index" />
            <Stack.Screen name="settings" options={{ presentation: 'fullScreenModal' }} />
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
    </MyUserContext.Provider>
  );
}