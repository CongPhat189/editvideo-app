import { router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use } from 'react';
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import DrawerScreen from '@/components/DrawerScreen';
import { AgentIcon, ChevronRightIcon, FolderIcon, PlanIcon, PlayIcon } from '@/components/HomeIcons';
import { MyUserContext } from '@/config/Contexts';
import { useThemeColors, useThemeStyles } from '@/constants/theme';
import useTopBarSpace from '@/hooks/useTopBarSpace';

const WIDE_SCREEN = 768;

export default function Home() {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

  const [user] = use(MyUserContext);
  const { width } = useWindowDimensions();
  const topBarSpace = useTopBarSpace();

  return (
    <DrawerScreen root>
      {(menuButton) => (
        <>
          <StatusBar style={colors.backgroundDeep === '#000000' ? 'light' : 'dark'} />
          <SafeAreaView style={styles.page}>
            <View style={[styles.topBar, { paddingTop: topBarSpace }]}>
              {menuButton}
            </View>

            <View style={[styles.content, { paddingHorizontal: width >= WIDE_SCREEN ? 32 : 20 }]}>
              <View style={styles.welcome}>
                <Text style={styles.eyebrow}>AI EDIT</Text>
                <Text style={styles.greeting}>Xin chào{user?.full_name ? `, ${user.full_name}` : ''}</Text>
                <Text style={styles.subtitle}>Bạn muốn tạo video gì hôm nay?</Text>
              </View>

              <Pressable
                onPress={() => router.push('/projects/new')}
                style={({ pressed }) => [styles.startCard, pressed && styles.pressed]}
                accessibilityRole="button"
                accessibilityLabel="Bắt đầu dự án mới"
              >
                <View style={styles.cardIcon}><FolderIcon size={22} /></View>
                <View style={styles.cardCopy}>
                  <Text style={styles.cardTitle}>Bắt đầu trò chuyện mới</Text>
                  <Text style={styles.cardSubtitle}>Chọn Agent và mô tả ý tưởng video của bạn</Text>
                </View>
                <ChevronRightIcon size={20} color={colors.textSecondary} />
              </Pressable>

              <View style={styles.suggestions}>
                <Text style={styles.sectionTitle}>Bạn có thể bắt đầu bằng cách</Text>
                <Suggestion Icon={PlayIcon} label="Lên ý tưởng cho video mới" />
                <Suggestion Icon={AgentIcon} label="Viết kịch bản video ngắn" />
                <Suggestion Icon={PlanIcon} label="Lập lịch nội dung tuần này" />
              </View>
            </View>
          </SafeAreaView>
        </>
      )}
    </DrawerScreen>
  );
}

function Suggestion({ Icon, label }) {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

  return (
    <View style={styles.suggestion}>
      <Icon size={18} color={colors.textSecondary} />
      <Text style={styles.suggestionText}>{label}</Text>
    </View>
  );
}

const createStyles = (colors) => StyleSheet.create({
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
    paddingVertical: 28,
  },
  welcome: {
    width: '100%',
    maxWidth: 560,
    marginBottom: 28,
  },
  eyebrow: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1.8,
    textAlign: 'center',
    marginBottom: 12,
  },
  greeting: {
    maxWidth: 560,
    color: colors.text,
    fontSize: 30,
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
  startCard: {
    width: '100%',
    maxWidth: 560,
    minHeight: 84,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 16,
    borderRadius: 24,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.divider,
    backgroundColor: colors.surface,
  },
  cardIcon: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 15,
    backgroundColor: colors.background,
  },
  cardCopy: { flex: 1, gap: 4 },
  cardTitle: { color: colors.text, fontSize: 16, fontWeight: '600' },
  cardSubtitle: { color: colors.textSecondary, fontSize: 13, lineHeight: 18 },
  pressed: { opacity: 0.72 },
  suggestions: {
    width: '100%',
    maxWidth: 560,
    marginTop: 28,
    gap: 16,
  },
  sectionTitle: {
    color: colors.textMuted,
    fontSize: 13,
    fontWeight: '600',
    marginBottom: 2,
  },
  suggestion: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  suggestionText: { color: colors.textSecondary, fontSize: 14 },
});
