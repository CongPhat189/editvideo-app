import { StatusBar } from 'expo-status-bar';
import { use } from 'react';
import { StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import DrawerScreen from '@/components/DrawerScreen';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import useTopBarSpace from '@/hooks/useTopBarSpace';

const WIDE_SCREEN = 768;

export default function Home() {
  const [user] = use(MyUserContext);
  const { width } = useWindowDimensions();
  const topBarSpace = useTopBarSpace();

  return (
    <DrawerScreen root>
      {(menuButton) => (
        <>
          <StatusBar style="light" />
          <SafeAreaView style={styles.page}>
            <View style={[styles.topBar, { paddingTop: topBarSpace }]}>
              {menuButton}
            </View>

            <View style={[styles.content, { paddingHorizontal: width >= WIDE_SCREEN ? 32 : 20 }]}>
              <Text style={styles.greeting}>Xin chào, {user?.full_name}</Text>
              <Text style={styles.subtitle}>Hôm nay bạn muốn làm video gì?</Text>
            </View>
          </SafeAreaView>
        </>
      )}
    </DrawerScreen>
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
    paddingBottom: 4,
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
