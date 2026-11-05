import { router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { BackIcon } from '@/components/HomeIcons';
import { useAppTheme, useThemeColors, useThemeStyles } from '@/constants/theme';

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

      <View style={styles.content}>
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
                <Text style={[styles.themeChoiceText, selected && styles.themeChoiceTextSelected]}>{label}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>
    </View>
  );
}

const createStyles = (colors) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.backgroundDeep,
  },
  header: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.divider,
  },
  backButton: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 20,
  },
  title: {
    color: colors.text,
    fontSize: 17,
    fontWeight: '600',
  },
  headerSpacer: {
    width: 40,
  },
  content: {
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
    padding: 20,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '600',
  },
  description: {
    color: colors.textSecondary,
    fontSize: 14,
    marginTop: 6,
  },
  themeCard: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 18,
    padding: 6,
    borderRadius: 16,
    backgroundColor: colors.surface,
  },
  themeChoice: {
    flex: 1,
    minHeight: 46,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
  },
  themeChoiceSelected: {
    backgroundColor: colors.primary,
  },
  themeChoiceText: {
    color: colors.textSecondary,
    fontSize: 15,
    fontWeight: '600',
  },
  themeChoiceTextSelected: {
    color: colors.onPrimary,
  },
  pressed: {
    opacity: 0.7,
  },
});
