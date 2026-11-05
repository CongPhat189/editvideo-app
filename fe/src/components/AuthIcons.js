import Svg, { Circle, G, Path, Rect } from 'react-native-svg';

import { useThemeColors } from '@/constants/theme';

const ACCENT_OPACITY = 0.24;

// Icon kiểu duotone: nét mảnh phía trên, lớp phủ màu nhạt phía dưới (accent).
// Nét màu trung tính thì lớp phủ là vàng champagne; nét có màu riêng (vàng, đỏ, chữ trên nền vàng) thì phủ cùng màu đó.
export const Icon = ({ children, accent, color, size = 20, strokeWidth = 1.6 }) => {
  const colors = useThemeColors();
  const stroke = color ?? colors.textMuted;
  const neutral = [colors.text, colors.textSecondary, colors.textMuted].includes(stroke);
  const accentColor = neutral ? colors.gold : stroke;

  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={stroke}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {accent ? (
        <G fill={accentColor} fillOpacity={ACCENT_OPACITY} stroke="none">
          {accent}
        </G>
      ) : null}
      {children}
    </Svg>
  );
};

export const PhoneIcon = (props) => (
  <Icon
    {...props}
    accent={<Path d="M13.832 16.568a1 1 0 0 0 1.213-.303l.355-.465A2 2 0 0 1 17 15h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.8 1.6l-.468.351a1 1 0 0 0-.292 1.233 14 14 0 0 0 6.392 6.384" />}
  >
    <Path d="M13.832 16.568a1 1 0 0 0 1.213-.303l.355-.465A2 2 0 0 1 17 15h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.8 1.6l-.468.351a1 1 0 0 0-.292 1.233 14 14 0 0 0 6.392 6.384" />
  </Icon>
);

export const LockIcon = (props) => (
  <Icon {...props} accent={<Rect x={4} y={11} width={16} height={10} rx={2.5} />}>
    <Rect x={4} y={11} width={16} height={10} rx={2.5} />
    <Path d="M8 11V7.5a4 4 0 0 1 8 0V11" />
    <Path d="M12 15v2" />
  </Icon>
);

export const UserIcon = (props) => (
  <Icon
    {...props}
    accent={
      <>
        <Circle cx={12} cy={8} r={4} />
        <Path d="M4.5 21a7.5 7.5 0 0 1 15 0Z" />
      </>
    }
  >
    <Circle cx={12} cy={8} r={4} />
    <Path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
  </Icon>
);
