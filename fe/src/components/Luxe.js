import { useId } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Svg, { Defs, Ellipse, LinearGradient, RadialGradient, Rect, Stop } from 'react-native-svg';

import { Breathing, Shimmer } from '@/components/Motion';
import { fonts, useThemeColors, useThemeStyles } from '@/constants/theme';

// Các lớp trang trí dùng chung: chỉ để hiển thị, không nhận thao tác

const useGradientId = (prefix) => `${prefix}${useId().replace(/[^a-zA-Z0-9]/g, '')}`;

// Nền vàng champagne chuyển sắc, phủ kín khung cha (khung cha tự bo góc và overflow: 'hidden')
export function GoldGradient({ style, angle = 'diagonal' }) {
  const colors = useThemeColors();
  const id = useGradientId('gold');
  const end = angle === 'vertical' ? { x2: '0', y2: '1' } : { x2: '1', y2: '1' };

  return (
    <Svg style={[StyleSheet.absoluteFill, style]} width="100%" height="100%" pointerEvents="none">
      <Defs>
        <LinearGradient id={id} x1="0" y1="0" {...end}>
          <Stop offset="0" stopColor={colors.goldLight} />
          <Stop offset="0.55" stopColor={colors.gold} />
          <Stop offset="1" stopColor={colors.goldDeep} />
        </LinearGradient>
      </Defs>
      <Rect width="100%" height="100%" fill={`url(#${id})`} />
    </Svg>
  );
}

// Quầng sáng mờ phía sau nội dung, tạo chiều sâu cho các màn hình chính
export function AmbientGlow({ height = 420, intensity = 1 }) {
  const colors = useThemeColors();
  const id = useGradientId('glow');
  const idSoft = useGradientId('glowSoft');

  return (
    <Breathing style={[styles.glowLayer, { height }]} duration={6000} scaleTo={1.06} opacityFrom={0.75} opacityTo={1}>
      <Svg width="100%" height="100%" pointerEvents="none">
        <Defs>
          <RadialGradient id={id} cx="50%" cy="0%" rx="70%" ry="80%">
            <Stop offset="0" stopColor={colors.glow} stopOpacity={0.22 * intensity} />
            <Stop offset="0.5" stopColor={colors.glow} stopOpacity={0.06 * intensity} />
            <Stop offset="1" stopColor={colors.glow} stopOpacity="0" />
          </RadialGradient>
          <RadialGradient id={idSoft} cx="85%" cy="15%" rx="45%" ry="45%">
            <Stop offset="0" stopColor={colors.goldLight} stopOpacity={0.08 * intensity} />
            <Stop offset="1" stopColor={colors.goldLight} stopOpacity="0" />
          </RadialGradient>
        </Defs>
        <Rect width="100%" height="100%" fill={`url(#${id})`} />
        <Ellipse cx="85%" cy="15%" rx="45%" ry="45%" fill={`url(#${idSoft})`} />
      </Svg>
    </Breathing>
  );
}

// Biểu tượng thương hiệu: chữ cái trên nền vàng chuyển sắc
export function BrandMark({ size = 40, letter = 'N', shimmer = false }) {
  const themed = useThemeStyles(createStyles);
  const radius = Math.round(size * 0.3);

  return (
    <View style={[themed.brandMark, { width: size, height: size, borderRadius: radius }]}>
      <GoldGradient />
      {shimmer ? <Shimmer interval={3600} /> : null}
      <Text style={[themed.brandLetter, { fontSize: size * 0.52, lineHeight: size * 0.62 }]}>{letter}</Text>
    </View>
  );
}

// Dòng chữ nhỏ viết hoa, giãn chữ, màu vàng: dùng làm nhãn phía trên tiêu đề
export function Eyebrow({ children, style, align = 'left' }) {
  const themed = useThemeStyles(createStyles);
  return <Text style={[themed.eyebrow, { textAlign: align }, style]}>{children}</Text>;
}

// Đường kẻ mảnh hai đầu nhạt dần, có chấm vàng ở giữa
export function Ornament({ width = 120, style }) {
  const colors = useThemeColors();
  const id = useGradientId('orn');
  return (
    <View style={[{ width, height: 7, alignSelf: 'center' }, style]} pointerEvents="none">
      <Svg width={width} height={7}>
        <Defs>
          <LinearGradient id={id} x1="0" y1="0" x2="1" y2="0">
            <Stop offset="0" stopColor={colors.gold} stopOpacity="0" />
            <Stop offset="0.5" stopColor={colors.gold} stopOpacity="0.9" />
            <Stop offset="1" stopColor={colors.gold} stopOpacity="0" />
          </LinearGradient>
        </Defs>
        <Rect x="0" y="3" width={width} height="1" fill={`url(#${id})`} />
        <Rect x={width / 2 - 3} y="0.5" width="6" height="6" fill={colors.gold} transform={`rotate(45 ${width / 2} 3.5)`} />
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  glowLayer: {
    pointerEvents: 'none',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
  },
});

const createStyles = (colors) => StyleSheet.create({
  brandMark: {
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.goldBorder,
  },
  brandLetter: {
    color: colors.onPrimary,
    fontFamily: fonts.display,
    fontWeight: '700',
    includeFontPadding: false,
  },
  eyebrow: {
    color: colors.gold,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 2.4,
    textTransform: 'uppercase',
  },
});
