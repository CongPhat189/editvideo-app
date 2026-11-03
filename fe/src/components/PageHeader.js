import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { BackIcon } from '@/components/HomeIcons';
import { colors } from '@/constants/theme';

const goBack = () => {
  if (router.canGoBack()) router.back();
  else router.replace('/');
};

export default function PageHeader({ title }) {
  return (
    <View style={styles.header}>
      <Pressable
        onPress={goBack}
        hitSlop={2}
        style={({ pressed }) => [styles.backButton, pressed && styles.pressed]}
        accessibilityRole="button"
        accessibilityLabel="Quay lại"
      >
        <BackIcon size={22} />
      </Pressable>
      <Text style={styles.title} numberOfLines={1}>{title}</Text>
      <View style={styles.spacer} />
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 4,
  },
  backButton: {
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
  title: {
    flex: 1,
    color: colors.text,
    fontSize: 17,
    fontWeight: '600',
    textAlign: 'center',
  },
  spacer: {
    width: 44,
  },
});
