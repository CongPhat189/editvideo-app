import { Pressable, StyleSheet } from 'react-native';

import { MenuIcon } from '@/components/HomeIcons';
import { colors } from '@/constants/theme';

export default function MenuButton({ expanded, onPress }) {
  return (
    <Pressable
      onPress={onPress}
      hitSlop={2}
      style={({ pressed }) => [styles.button, pressed && styles.pressed]}
      accessibilityRole="button"
      accessibilityLabel="Mở menu"
      aria-expanded={expanded}
    >
      <MenuIcon size={22} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
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
});
