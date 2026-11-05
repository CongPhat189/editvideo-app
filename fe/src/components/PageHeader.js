import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { BackIcon } from '@/components/HomeIcons';
import { fonts, useThemeStyles } from '@/constants/theme';
import useTopBarSpace from '@/hooks/useTopBarSpace';

const goBack = () => {
  if (router.canGoBack()) router.back();
  else router.replace('/');
};

export default function PageHeader({ title, left }) {
  const styles = useThemeStyles(createStyles);

  const topBarSpace = useTopBarSpace();

  return (
    <View style={[styles.header, { paddingTop: topBarSpace }]}>
      {left ?? (
        <Pressable
          onPress={goBack}
          hitSlop={2}
          style={({ pressed }) => [styles.backButton, pressed && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel="Quay lại"
        >
          <BackIcon size={22} />
        </Pressable>
      )}
      <Text style={styles.title} numberOfLines={1}>{title}</Text>
      <View style={styles.spacer} />
    </View>
  );
}

const createStyles = (colors) => StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 16,
    paddingBottom: 6,
  },
  backButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 22,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
  },
  pressed: {
    opacity: 0.7,
    transform: [{ scale: 0.96 }],
  },
  title: {
    flex: 1,
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 19,
    fontWeight: '600',
    letterSpacing: 0.2,
    textAlign: 'center',
  },
  spacer: {
    width: 44,
  },
});
