import { Stack } from 'expo-router';
import { useReducer } from 'react';

import { MyUserContext } from '@/config/Contexts';
import { MyUserReducer } from '@/reducers/reducers';

export default function RootLayout() {
  const [user, dispatch] = useReducer(MyUserReducer, null);

  return (
    <MyUserContext.Provider value={[user, dispatch]}>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Protected guard={!!user}>
          <Stack.Screen name="index" />
          <Stack.Screen name="settings" options={{ presentation: 'fullScreenModal' }} />
          <Stack.Screen name="projects/new" />
          <Stack.Screen name="projects/[id]/index" />
          <Stack.Screen name="projects/[id]/schedule" />
          <Stack.Screen name="scheduled" />
          <Stack.Screen name="agents/index" />
          <Stack.Screen name="agents/new" />
        </Stack.Protected>
        <Stack.Protected guard={!user}>
          <Stack.Screen name="login" />
          <Stack.Screen name="register" />
        </Stack.Protected>
      </Stack>
    </MyUserContext.Provider>
  );
}