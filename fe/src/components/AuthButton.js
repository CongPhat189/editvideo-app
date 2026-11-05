import { useRef } from 'react';
import { ActivityIndicator, Animated, Platform, Pressable, StyleSheet, Text } from 'react-native';

import { GoldGradient } from '@/components/Luxe';
import { Shimmer } from '@/components/Motion';
import { useThemeColors, useThemeStyles } from '@/constants/theme';

const NATIVE = Platform.OS !== 'web';

export default function AuthButton({ title, onPress, loading = false, disabled = false, variant = 'primary' }) {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);
  const scale = useRef(new Animated.Value(1)).current;

  const isPrimary = variant === 'primary';
  const inactive = loading || disabled;

  // Nhấn xuống thì nút lún nhẹ, thả ra thì bật lại
  const springTo = (toValue) => {
    Animated.spring(scale, { toValue, friction: 6, tension: 220, useNativeDriver: NATIVE }).start();
  };

  return (
    <Animated.View style={{ transform: [{ scale }] }}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ busy: loading, disabled: inactive }}
        disabled={inactive}
        onPress={onPress}
        onPressIn={() => springTo(0.97)}
        onPressOut={() => springTo(1)}
        style={({ pressed }) => [
          styles.button,
          isPrimary ? styles.primary : styles.secondary,
          disabled && !loading && styles.disabled,
          pressed && styles.pressed,
        ]}
      >
        {isPrimary ? <GoldGradient /> : null}
        {isPrimary && !inactive ? <Shimmer /> : null}
        {loading ? (
          <ActivityIndicator color={isPrimary ? colors.onPrimary : colors.gold} />
        ) : (
          <Text style={[styles.title, !isPrimary && styles.secondaryTitle]}>{title}</Text>
        )}
      </Pressable>
    </Animated.View>
  );
}

const createStyles = (colors) => StyleSheet.create({
  button: {
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 14,
    overflow: 'hidden',
  },
  primary: {
    backgroundColor: colors.primary,
    shadowColor: colors.glow,
    shadowOpacity: 0.3,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
    elevation: 3,
  },
  secondary: {
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
  },
  disabled: {
    opacity: 0.5,
  },
  pressed: {
    opacity: 0.9,
  },
  title: {
    color: colors.onPrimary,
    fontSize: 15.5,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  secondaryTitle: {
    color: colors.text,
    fontWeight: '600',
  },
});
