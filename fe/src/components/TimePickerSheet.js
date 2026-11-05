import { useEffect, useState } from 'react';
import { Animated, Easing, Modal, Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import AuthButton from '@/components/AuthButton';
import { CloseIcon } from '@/components/HomeIcons';
import TimeWheel, { CENTER_ROW, ROW_HEIGHT } from '@/components/TimeWheel';
import { fonts, useThemeStyles } from '@/constants/theme';
import useReducedMotion from '@/hooks/useReducedMotion';

const OPEN_DURATION = 280;
const CLOSE_DURATION = 200;

export default function TimePickerSheet({
  visible,
  title,
  hour,
  minute,
  error,
  saving,
  onChangeHour,
  onChangeMinute,
  onSave,
  onClose,
  onClosed,
}) {
  const styles = useThemeStyles(createStyles);

  const insets = useSafeAreaInsets();
  const { height } = useWindowDimensions();
  const reducedMotion = useReducedMotion();
  const [progress] = useState(() => new Animated.Value(0));
  const [mounted, setMounted] = useState(visible);
  if (visible && !mounted) setMounted(true);

  useEffect(() => {
    const duration = visible ? OPEN_DURATION : CLOSE_DURATION;
    Animated.timing(progress, {
      toValue: visible ? 1 : 0,
      duration: reducedMotion ? 0 : duration,
      easing: visible ? Easing.out(Easing.cubic) : Easing.in(Easing.cubic),
      useNativeDriver: true,
    }).start(({ finished }) => {
      if (!finished || visible) return;
      setMounted(false);
      onClosed();
    });
  }, [visible, progress, reducedMotion, onClosed]);

  const translateY = progress.interpolate({ inputRange: [0, 1], outputRange: [height, 0] });

  return (
    <Modal visible={mounted} transparent animationType="none" statusBarTranslucent onRequestClose={onClose}>
      <Animated.View style={[styles.dim, { opacity: progress }]}>
        <Pressable style={styles.flex} onPress={onClose} accessibilityRole="button" accessibilityLabel="Đóng" />
      </Animated.View>
      <Animated.View style={[styles.sheet, { paddingBottom: insets.bottom + 16, transform: [{ translateY }] }]}>
        <View style={styles.handle} />
        <View style={styles.header}>
          <Text style={styles.title} numberOfLines={1}>{title}</Text>
          <Pressable
            onPress={onClose}
            style={({ pressed }) => [styles.close, pressed && styles.pressed]}
            accessibilityRole="button"
            accessibilityLabel="Đóng"
          >
            <CloseIcon size={18} />
          </Pressable>
        </View>

        <View style={styles.wheels}>
          <View style={styles.band} pointerEvents="none" />
          <TimeWheel count={24} initialValue={hour} label="Giờ" onChange={onChangeHour} />
          <TimeWheel count={60} initialValue={minute} label="Phút" onChange={onChangeMinute} />
        </View>

        {error ? <Text style={styles.error}>{error}</Text> : null}
        <AuthButton title="Lưu lịch" onPress={onSave} loading={saving} />
      </Animated.View>
    </Modal>
  );
}

const createStyles = (colors) => StyleSheet.create({
  flex: {
    flex: 1,
  },
  dim: {
    flex: 1,
    backgroundColor: colors.overlay,
  },
  sheet: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 18,
    paddingTop: 10,
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    borderWidth: StyleSheet.hairlineWidth,
    borderBottomWidth: 0,
    borderColor: colors.goldBorder,
    backgroundColor: colors.backgroundDeep,
    shadowColor: colors.shadow,
    shadowOpacity: 0.3,
    shadowRadius: 30,
    shadowOffset: { width: 0, height: -8 },
    elevation: 16,
  },
  handle: {
    alignSelf: 'center',
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.borderStrong,
    marginBottom: 8,
  },
  header: {
    minHeight: 48,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  title: {
    flex: 1,
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 19,
    fontWeight: '600',
  },
  close: {
    width: 38,
    height: 38,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 19,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
  },
  pressed: {
    opacity: 0.7,
  },
  wheels: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 24,
    marginBottom: 18,
  },
  band: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: CENTER_ROW * ROW_HEIGHT,
    height: ROW_HEIGHT,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
  },
  error: {
    color: colors.error,
    fontSize: 13.5,
    textAlign: 'center',
    marginBottom: 12,
  },
});
