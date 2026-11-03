import { StatusBar } from 'expo-status-bar';
import { use, useCallback, useState } from 'react';
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { MenuIcon } from '@/components/HomeIcons';
import PushDrawer from '@/components/PushDrawer';
import Sidebar from '@/components/Sidebar';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';

const WIDE_SCREEN = 768;

export default function Home() {
  const [user] = use(MyUserContext);
  const { width } = useWindowDimensions();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const closeSidebar = useCallback(() => setSidebarOpen(false), []);

  return (
    <PushDrawer open={sidebarOpen} onClose={closeSidebar} drawer={<Sidebar onClose={closeSidebar} />}>
      <StatusBar style="light" />
      <SafeAreaView style={styles.page}>
        <View style={styles.topBar}>
          <Pressable
            onPress={() => setSidebarOpen(true)}
            hitSlop={2}
            style={({ pressed }) => [styles.menuButton, pressed && styles.pressed]}
            accessibilityRole="button"
            accessibilityLabel="Mở menu"
            aria-expanded={sidebarOpen}
          >
            <MenuIcon size={22} />
          </Pressable>
        </View>

        <View style={[styles.content, { paddingHorizontal: width >= WIDE_SCREEN ? 32 : 20 }]}>
          <Text style={styles.greeting}>Xin chào, {user?.full_name}</Text>
          <Text style={styles.subtitle}>Hôm nay bạn muốn làm video gì?</Text>
        </View>
      </SafeAreaView>
    </PushDrawer>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: colors.background,
  },
  topBar: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 4,
  },
  menuButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 22,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.divider,
    backgroundColor: colors.surface,
  },
  pressed: {
    opacity: 0.7,
  },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  greeting: {
    maxWidth: 560,
    color: colors.text,
    fontSize: 28,
    fontWeight: '700',
    textAlign: 'center',
  },
  subtitle: {
    maxWidth: 560,
    color: colors.textSecondary,
    fontSize: 16,
    lineHeight: 24,
    textAlign: 'center',
    marginTop: 8,
  },
});
