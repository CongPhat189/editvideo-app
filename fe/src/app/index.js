import { router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use } from 'react';
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import DrawerScreen from '@/components/DrawerScreen';
import { ChevronRightIcon, ClapperIcon, IdeaIcon, PlanIcon, ScriptIcon } from '@/components/HomeIcons';
import { AmbientGlow, Eyebrow, GoldGradient, Ornament } from '@/components/Luxe';
import { FadeIn, Shimmer, stagger } from '@/components/Motion';
import { MyUserContext } from '@/config/Contexts';
import { fonts, useThemeColors, useThemeStyles } from '@/constants/theme';
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
          <StatusBar style={colors.statusBar} />
          <SafeAreaView style={styles.page}>
            <AmbientGlow height={480} />
            <View style={[styles.topBar, { paddingTop: topBarSpace }]}>
              {menuButton}
            </View>

            <View style={[styles.content, { paddingHorizontal: width >= WIDE_SCREEN ? 32 : 20 }]}>
              <FadeIn style={styles.welcome} distance={18}>
                <Eyebrow align="center" style={styles.eyebrow}>AI Edit · Video Studio</Eyebrow>
                <Text style={styles.greeting}>Xin chào{user?.full_name ? `, ${user.full_name}` : ''}</Text>
                <Ornament width={110} style={styles.ornament} />
                <Text style={styles.subtitle}>Bạn muốn tạo video gì hôm nay?</Text>
              </FadeIn>

              <FadeIn style={styles.block} delay={160} distance={22}>
              <Pressable
                onPress={() => router.push('/projects/new')}
                style={({ pressed }) => [styles.startCard, pressed && styles.pressed]}
                accessibilityRole="button"
                accessibilityLabel="Bắt đầu dự án mới"
              >
                <View style={styles.cardIcon}>
                  <GoldGradient />
                  <Shimmer interval={2600} />
                  <View><ClapperIcon size={24} color={colors.onPrimary} /></View>
                </View>
                <View style={styles.cardCopy}>
                  <Text style={styles.cardTitle}>Bắt đầu trò chuyện mới</Text>
                  <Text style={styles.cardSubtitle}>Chọn Agent và mô tả ý tưởng video của bạn</Text>
                </View>
                <View style={styles.cardArrow}>
                  <ChevronRightIcon size={18} color={colors.gold} />
                </View>
              </Pressable>
              </FadeIn>

              <View style={styles.suggestions}>
                <FadeIn delay={300}>
                  <Text style={styles.sectionTitle}>Bạn có thể bắt đầu bằng cách</Text>
                </FadeIn>
                <Suggestion Icon={IdeaIcon} label="Lên ý tưởng cho video mới" delay={stagger(0, 80, 360)} />
                <Suggestion Icon={ScriptIcon} label="Viết kịch bản video ngắn" delay={stagger(1, 80, 360)} />
                <Suggestion Icon={PlanIcon} label="Lập lịch nội dung tuần này" delay={stagger(2, 80, 360)} />
              </View>
            </View>
          </SafeAreaView>
        </>
      )}
    </DrawerScreen>
  );
}

function Suggestion({ Icon, label, delay }) {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

  return (
    <FadeIn style={styles.suggestion} delay={delay} distance={16}>
      <View style={styles.suggestionIcon}>
        <Icon size={18} color={colors.gold} />
      </View>
      <Text style={styles.suggestionText}>{label}</Text>
    </FadeIn>
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
    alignItems: 'center',
    marginBottom: 32,
  },
  eyebrow: {
    marginBottom: 14,
  },
  greeting: {
    maxWidth: 560,
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 34,
    lineHeight: 42,
    fontWeight: '600',
    letterSpacing: 0.2,
    textAlign: 'center',
  },
  ornament: {
    marginTop: 16,
    marginBottom: 14,
  },
  subtitle: {
    maxWidth: 560,
    color: colors.textSecondary,
    fontSize: 16,
    lineHeight: 24,
    textAlign: 'center',
  },
  block: {
    width: '100%',
    maxWidth: 560,
  },
  startCard: {
    width: '100%',
    maxWidth: 560,
    minHeight: 92,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    paddingVertical: 18,
    paddingHorizontal: 18,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.card,
    shadowColor: colors.glow,
    shadowOpacity: 0.18,
    shadowRadius: 28,
    shadowOffset: { width: 0, height: 12 },
    elevation: 5,
  },
  cardIcon: {
    width: 52,
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 16,
    overflow: 'hidden',
  },
  cardCopy: { flex: 1, gap: 5 },
  cardTitle: { color: colors.text, fontSize: 17, fontWeight: '700', letterSpacing: 0.1 },
  cardSubtitle: { color: colors.textSecondary, fontSize: 13.5, lineHeight: 19 },
  cardArrow: {
    width: 34,
    height: 34,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 17,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
  },
  pressed: { opacity: 0.85, transform: [{ scale: 0.99 }] },
  suggestions: {
    width: '100%',
    maxWidth: 560,
    marginTop: 30,
    gap: 10,
  },
  sectionTitle: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.8,
    textTransform: 'uppercase',
    marginBottom: 4,
    marginLeft: 4,
  },
  suggestion: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    minHeight: 54,
    paddingHorizontal: 14,
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  suggestionIcon: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 10,
    backgroundColor: colors.goldSoft,
  },
  suggestionText: { flex: 1, color: colors.text, fontSize: 14.5 },
});
