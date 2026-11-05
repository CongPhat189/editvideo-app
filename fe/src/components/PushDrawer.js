import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Animated,
  BackHandler,
  Easing,
  Pressable,
  StyleSheet,
  useWindowDimensions,
  View,
} from 'react-native';

import { useThemeStyles } from '@/constants/theme';
import useReducedMotion from '@/hooks/useReducedMotion';

const OPEN_DURATION = 280;
const CLOSE_DURATION = 200;
const MAX_WIDTH = 320;
const WIDTH_RATIO = 0.76;
const CONTENT_RADIUS = 36;

export default function PushDrawer({ open, onClose, drawer, children }) {
  const styles = useThemeStyles(createStyles);

  const { width } = useWindowDimensions();
  const drawerWidth = Math.min(width * WIDTH_RATIO, MAX_WIDTH);
  const reducedMotion = useReducedMotion();
  const progress = useRef(new Animated.Value(open ? 1 : 0)).current;
  const [mounted, setMounted] = useState(open);

  if (open && !mounted) setMounted(true);

  useEffect(() => {
    const duration = open ? OPEN_DURATION : CLOSE_DURATION;
    Animated.timing(progress, {
      toValue: open ? 1 : 0,
      duration: reducedMotion ? 0 : duration,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start(({ finished }) => {
      if (finished && !open) setMounted(false);
    });
  }, [open, progress, reducedMotion]);

  // Chỉ bắt nút Back khi màn hình này đang hiển thị, để Back ở trang Tài khoản vẫn đóng đúng trang đó
  useFocusEffect(
    useCallback(() => {
      if (!open) return undefined;
      const subscription = BackHandler.addEventListener('hardwareBackPress', () => {
        onClose();
        return true;
      });
      return () => subscription.remove();
    }, [open, onClose])
  );

  const translateX = progress.interpolate({ inputRange: [0, 1], outputRange: [0, drawerWidth] });

  return (
    <View style={styles.root}>
      {mounted ? (
        <View style={styles.drawerLayer}>
          <View style={[styles.drawer, { width: drawerWidth }]}>{drawer}</View>
        </View>
      ) : null}

      <Animated.View style={[styles.content, { transform: [{ translateX }] }]}>
        <View
          style={styles.contentInner}
          accessibilityElementsHidden={open}
          importantForAccessibility={open ? 'no-hide-descendants' : 'auto'}
        >
          {children}
        </View>
        {mounted ? (
          <Animated.View style={[styles.dim, { opacity: progress }]} pointerEvents="none" />
        ) : null}
        {open ? (
          <Pressable
            style={StyleSheet.absoluteFill}
            onPress={onClose}
            accessibilityRole="button"
            accessibilityLabel="Đóng menu"
          />
        ) : null}
      </Animated.View>
    </View>
  );
}

const createStyles = (colors) => StyleSheet.create({
  root: {
    flex: 1,
    overflow: 'hidden',
    backgroundColor: colors.background,
  },
  drawerLayer: {
    ...StyleSheet.absoluteFill,
    backgroundColor: colors.backgroundDeep,
  },
  drawer: {
    flex: 1,
  },
  content: {
    flex: 1,
    overflow: 'hidden',
    backgroundColor: colors.background,
    borderTopLeftRadius: CONTENT_RADIUS,
    borderBottomLeftRadius: CONTENT_RADIUS,
  },
  contentInner: {
    flex: 1,
  },
  dim: {
    ...StyleSheet.absoluteFill,
    backgroundColor: colors.overlay,
  },
});
