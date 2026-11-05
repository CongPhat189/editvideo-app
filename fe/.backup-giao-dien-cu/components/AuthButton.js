import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';

import { useThemeColors, useThemeStyles } from '@/constants/theme';

export default function AuthButton({ title, onPress, loading = false, variant = 'primary' }) {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

  const isPrimary = variant === 'primary';

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ busy: loading, disabled: loading }}
      disabled={loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        isPrimary ? styles.primary : styles.secondary,
        pressed && styles.pressed,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={isPrimary ? colors.onPrimary : colors.text} />
      ) : (
        <Text style={[styles.title, !isPrimary && styles.secondaryTitle]}>{title}</Text>
      )}
    </Pressable>
  );
}

const createStyles = (colors) => StyleSheet.create({
  button: {
    height: 46,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 10,
  },
  primary: {
    backgroundColor: colors.primary,
  },
  secondary: {
    backgroundColor: colors.surface,
  },
  pressed: {
    opacity: 0.8,
  },
  title: {
    color: colors.onPrimary,
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryTitle: {
    color: colors.text,
  },
});