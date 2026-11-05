import { useEffect, useId, useRef, useState } from 'react';
import { Animated, Easing, Platform, StyleSheet, View } from 'react-native';
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg';

import { useThemeColors, useThemeStyles } from '@/constants/theme';
import useReducedMotion from '@/hooks/useReducedMotion';

// Các hiệu ứng chuyển động dùng chung, chỉ để hiển thị.
// Máy bật "Giảm chuyển động" thì nội dung hiện ngay, không chạy hiệu ứng.

const NATIVE = Platform.OS !== 'web';
const EASE_OUT = Easing.bezier(0.22, 1, 0.36, 1);

// Hiện dần và trượt nhẹ vào chỗ. axis: 'y' (từ dưới lên) hoặc 'x' (từ trái sang)
export function FadeIn({ children, delay = 0, distance = 14, duration = 560, axis = 'y', style }) {
  const reducedMotion = useReducedMotion();
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animation = Animated.timing(progress, {
      toValue: 1,
      duration: reducedMotion ? 0 : duration,
      delay: reducedMotion ? 0 : delay,
      easing: EASE_OUT,
      useNativeDriver: NATIVE,
    });
    animation.start();
    return () => animation.stop();
  }, [progress, delay, duration, reducedMotion]);

  const offset = progress.interpolate({ inputRange: [0, 1], outputRange: [distance, 0] });
  const transform = axis === 'x' ? [{ translateX: offset }] : [{ translateY: offset }];

  return <Animated.View style={[style, { opacity: progress, transform }]}>{children}</Animated.View>;
}

// Bật ra nhẹ (phóng từ nhỏ lên) mỗi lần được dựng lại; đổi key để chạy lại
export function PopIn({ children, from = 0.6, style }) {
  const reducedMotion = useReducedMotion();
  const scale = useRef(new Animated.Value(reducedMotion ? 1 : from)).current;

  useEffect(() => {
    if (reducedMotion) {
      scale.setValue(1);
      return undefined;
    }
    const animation = Animated.spring(scale, { toValue: 1, friction: 5, tension: 160, useNativeDriver: NATIVE });
    animation.start();
    return () => animation.stop();
  }, [scale, reducedMotion]);

  return <Animated.View style={[style, { transform: [{ scale }] }]}>{children}</Animated.View>;
}

// "Thở" chậm: phóng to và mờ nhẹ theo chu kỳ, dùng cho logo và quầng sáng
export function Breathing({ children, duration = 2600, scaleTo = 1.04, opacityFrom = 1, opacityTo = 1, style }) {
  const reducedMotion = useReducedMotion();
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (reducedMotion) return undefined;
    const half = duration / 2;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(progress, { toValue: 1, duration: half, easing: Easing.inOut(Easing.sin), useNativeDriver: NATIVE }),
        Animated.timing(progress, { toValue: 0, duration: half, easing: Easing.inOut(Easing.sin), useNativeDriver: NATIVE }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [progress, duration, reducedMotion]);

  const scale = progress.interpolate({ inputRange: [0, 1], outputRange: [1, scaleTo] });
  const opacity = progress.interpolate({ inputRange: [0, 1], outputRange: [opacityFrom, opacityTo] });

  return <Animated.View style={[style, { opacity, transform: [{ scale }] }]}>{children}</Animated.View>;
}

// Vệt sáng lướt ngang qua bề mặt vàng theo chu kỳ (đặt trong khung cha có overflow: 'hidden')
export function Shimmer({ interval = 3200, duration = 1100 }) {
  const reducedMotion = useReducedMotion();
  const progress = useRef(new Animated.Value(0)).current;
  const [width, setWidth] = useState(0);
  const id = `shine${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  const band = 90;

  useEffect(() => {
    if (reducedMotion || !width) return undefined;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.delay(interval),
        Animated.timing(progress, { toValue: 1, duration, easing: Easing.inOut(Easing.quad), useNativeDriver: NATIVE }),
        Animated.timing(progress, { toValue: 0, duration: 0, useNativeDriver: NATIVE }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [progress, width, interval, duration, reducedMotion]);

  const translateX = progress.interpolate({ inputRange: [0, 1], outputRange: [-band * 1.5, width + band * 0.5] });

  return (
    <View
      style={StyleSheet.absoluteFill}
      pointerEvents="none"
      onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
    >
      {width ? (
        <Animated.View style={[styles.shineBand, { width: band, transform: [{ translateX }, { skewX: '-20deg' }] }]}>
          <Svg width={band} height="100%">
            <Defs>
              <LinearGradient id={id} x1="0" y1="0" x2="1" y2="0">
                <Stop offset="0" stopColor="#FFFFFF" stopOpacity="0" />
                <Stop offset="0.5" stopColor="#FFFFFF" stopOpacity="0.45" />
                <Stop offset="1" stopColor="#FFFFFF" stopOpacity="0" />
              </LinearGradient>
            </Defs>
            <Rect width={band} height="100%" fill={`url(#${id})`} />
          </Svg>
        </Animated.View>
      ) : null}
    </View>
  );
}

// Ba chấm nhảy lần lượt: Agent đang trả lời
export function TypingDots({ color }) {
  const colors = useThemeColors();
  const themed = useThemeStyles(createStyles);
  const reducedMotion = useReducedMotion();
  const dots = useRef([0, 1, 2].map(() => new Animated.Value(0))).current;

  useEffect(() => {
    if (reducedMotion) return undefined;
    const bounce = (value) =>
      Animated.sequence([
        Animated.timing(value, { toValue: 1, duration: 280, easing: Easing.out(Easing.quad), useNativeDriver: NATIVE }),
        Animated.timing(value, { toValue: 0, duration: 280, easing: Easing.in(Easing.quad), useNativeDriver: NATIVE }),
      ]);
    const loop = Animated.loop(
      Animated.sequence([Animated.stagger(140, dots.map(bounce)), Animated.delay(260)])
    );
    loop.start();
    return () => loop.stop();
  }, [dots, reducedMotion]);

  return (
    <View style={themed.dots}>
      {dots.map((value, index) => (
        <Animated.View
          key={index}
          style={[
            themed.dot,
            { backgroundColor: color ?? colors.gold },
            {
              opacity: value.interpolate({ inputRange: [0, 1], outputRange: [0.35, 1] }),
              transform: [{ translateY: value.interpolate({ inputRange: [0, 1], outputRange: [0, -4] }) }],
            },
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  shineBand: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
  },
});

const createStyles = () => StyleSheet.create({
  dots: {
    height: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
});

// Độ trễ so le cho danh sách, chặn trên để danh sách dài không phải chờ lâu
export const stagger = (index, step = 70, base = 0, max = 8) => base + Math.min(index, max) * step;
