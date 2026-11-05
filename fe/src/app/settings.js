import { router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { BackIcon, CheckIcon } from '@/components/HomeIcons';
import { Eyebrow } from '@/components/Luxe';
import { FadeIn, PopIn } from '@/components/Motion';
import { fonts, palettes, useAppTheme, useThemeColors, useThemeStyles } from '@/constants/theme';

export default function Settings() {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);
  const { theme, setTheme } = useAppTheme();
  const insets = useSafeAreaInsets();

  const goBack = () => {
    if (router.canGoBack()) router.back();
    else router.replace('/');
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <StatusBar style={theme === 'dark' ? 'light' : 'dark'} />
      <View style={styles.header}>
        <Pressable
          onPress={goBack}
          style={({ pressed }) => [styles.backButton, pressed && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel="Quay lại"
        >
          <BackIcon size={22} />
        </Pressable>
        <Text style={styles.title}>Cài đặt</Text>
        <View style={styles.headerSpacer} />
      </View>

      <FadeIn style={styles.content} distance={18}>
        <Eyebrow style={styles.eyebrow}>Tùy chỉnh</Eyebrow>
        <Text style={styles.sectionTitle}>Giao diện</Text>
        <Text style={styles.description}>Chọn giao diện bạn muốn sử dụng.</Text>
        <View style={styles.themeCard}>
          {[
            { value: 'light', label: 'Sáng' },
            { value: 'dark', label: 'Tối' },
          ].map(({ value, label }) => {
            const selected = theme === value;
            return (
              <Pressable
                key={value}
                onPress={() => setTheme(value)}
                style={[styles.themeChoice, selected && styles.themeChoiceSelected]}
                accessibilityRole="radio"
                accessibilityLabel={`Giao diện ${label.toLowerCase()}`}
                accessibilityState={{ selected }}
              >
                <View style={[styles.preview, { backgroundColor: palettes[value].background, borderColor: palettes[value].borderStrong }]}>
                  <View style={[styles.previewBar, { backgroundColor: palettes[value].gold }]} />
                  <View style={[styles.previewLine, { backgroundColor: palettes[value].textMuted }]} />
                  <View style={[styles.previewLine, styles.previewLineShort, { backgroundColor: palettes[value].divider }]} />
                  <View style={[styles.previewCard, { backgroundColor: palettes[value].card, borderColor: palettes[value].goldBorder }]} />
                </View>
                <View style={styles.choiceFooter}>
                  <Text style={[styles.themeChoiceText, selected && styles.themeChoiceTextSelected]}>{label}</Text>
                  <View style={[styles.radio, selected && styles.radioSelected]}>
                    {selected ? <PopIn><CheckIcon size={12} color={colors.onPrimary} /></PopIn> : null}
                  </View>
                </View>
              </Pressable>
            );
          })}
        </View>
      </FadeIn>
    </View>
  );
}

const createStyles = (colors) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    minHeight: 60,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.borderStrong,
  },
  backButton: {
    width: 42,
    height: 42,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 21,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
  },
  title: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 19,
    fontWeight: '600',
  },
  headerSpacer: {
    width: 42,
  },
  content: {
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
    padding: 20,
    paddingTop: 28,
  },
  eyebrow: {
    marginBottom: 8,
  },
  sectionTitle: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 26,
    fontWeight: '600',
  },
  description: {
    color: colors.textSecondary,
    fontSize: 14.5,
    marginTop: 6,
  },
  themeCard: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 22,
  },
  themeChoice: {
    flex: 1,
    padding: 10,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: colors.card,
  },
  themeChoiceSelected: {
    borderColor: colors.gold,
    backgroundColor: colors.goldSoft,
  },
  preview: {
    height: 96,
    padding: 10,
    gap: 6,
    borderRadius: 13,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: 'hidden',
  },
  previewBar: {
    width: 28,
    height: 6,
    borderRadius: 3,
  },
  previewLine: {
    width: '80%',
    height: 5,
    borderRadius: 3,
    opacity: 0.6,
  },
  previewLineShort: {
    width: '55%',
  },
  previewCard: {
    flex: 1,
    marginTop: 2,
    borderRadius: 8,
    borderWidth: 1,
  },
  choiceFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 4,
    paddingTop: 12,
    paddingBottom: 4,
  },
  themeChoiceText: {
    color: colors.textSecondary,
    fontSize: 15,
    fontWeight: '600',
  },
  themeChoiceTextSelected: {
    color: colors.text,
  },
  radio: {
    width: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: colors.borderStrong,
  },
  radioSelected: {
    borderColor: colors.gold,
    backgroundColor: colors.gold,
  },
  pressed: {
    opacity: 0.7,
  },
});
