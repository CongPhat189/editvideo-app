import { Pressable, StyleSheet } from 'react-native';

import { MenuIcon } from '@/components/HomeIcons';
import { useThemeStyles } from '@/constants/theme';

export default function MenuButton({ expanded, onPress }) {
  const styles = useThemeStyles(createStyles);

  return (
    <Pressable
      onPress={onPress}
      hitSlop={2}
      style={({ pressed }) => [styles.button, pressed && styles.pressed]}
      accessibilityRole="button"
      accessibilityLabel="Mở menu"
      aria-expanded={expanded}
    >
      <MenuIcon size={20} />
    </Pressable>
  );
}

const createStyles = (colors) => StyleSheet.create({
  button: {
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
});
