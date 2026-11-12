import { useId } from 'react';
import Svg, { Circle, Defs, G, Path, RadialGradient, Rect, Stop } from 'react-native-svg';

import { useThemeColors } from '@/constants/theme';

// Logo màu của từng nền tảng đăng bài, vẽ bằng SVG (không cần ảnh, không cần mạng)

const FacebookIcon = ({ size }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24">
    <Circle cx={12} cy={12} r={12} fill="#0866FF" />
    <Path
      fill="#FFFFFF"
      d="M13.6 24v-8.4h2.8l.45-3.3H13.6v-2.1c0-.95.27-1.6 1.63-1.6h1.75V5.65a23 23 0 0 0-2.55-.13c-2.52 0-4.25 1.54-4.25 4.37v2.4H7.33v3.3h2.85V24z"
    />
  </Svg>
);

const YouTubeIcon = ({ size }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24">
    <Rect x={0.5} y={4} width={23} height={16} rx={5} fill="#FF0000" />
    <Path d="M9.75 8.4v7.2L16 12z" fill="#FFFFFF" />
  </Svg>
);

const InstagramIcon = ({ size }) => {
  const id = `ig${useId().replace(/:/g, '')}`;
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Defs>
        <RadialGradient id={id} cx="0.3" cy="1.07" r="1.3" gradientUnits="objectBoundingBox">
          <Stop offset="0" stopColor="#FFD600" />
          <Stop offset="0.25" stopColor="#FF7A00" />
          <Stop offset="0.5" stopColor="#FF0069" />
          <Stop offset="0.75" stopColor="#D300C5" />
          <Stop offset="1" stopColor="#7638FA" />
        </RadialGradient>
      </Defs>
      <Rect x={0} y={0} width={24} height={24} rx={6.5} fill={`url(#${id})`} />
      <Rect x={5} y={5} width={14} height={14} rx={4.2} fill="none" stroke="#FFFFFF" strokeWidth={1.8} />
      <Circle cx={12} cy={12} r={3.3} fill="none" stroke="#FFFFFF" strokeWidth={1.8} />
      <Circle cx={16.2} cy={7.8} r={1.05} fill="#FFFFFF" />
    </Svg>
  );
};

const TIKTOK_NOTE =
  'M12.53.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z';

const TikTokIcon = ({ size }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24">
    <Rect x={0} y={0} width={24} height={24} rx={6.5} fill="#000000" />
    {/* Hai lớp lệch màu xanh / đỏ phía sau nốt nhạc trắng, giống logo gốc */}
    <G transform="translate(5.6 4.9) scale(0.56)">
      <Path d={TIKTOK_NOTE} fill="#25F4EE" transform="translate(-0.9 -0.9)" />
      <Path d={TIKTOK_NOTE} fill="#FE2C55" transform="translate(0.9 0.9)" />
      <Path d={TIKTOK_NOTE} fill="#FFFFFF" />
    </G>
  </Svg>
);

const WebsiteIcon = ({ size }) => {
  const colors = useThemeColors();
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={colors.gold} strokeWidth={1.6}>
      <Circle cx={12} cy={12} r={9.5} />
      <Path d="M2.5 12h19M12 2.5c2.6 2.6 3.9 5.8 3.9 9.5s-1.3 6.9-3.9 9.5c-2.6-2.6-3.9-5.8-3.9-9.5s1.3-6.9 3.9-9.5z" />
    </Svg>
  );
};

const ICONS = {
  Facebook: FacebookIcon,
  YouTube: YouTubeIcon,
  Instagram: InstagramIcon,
  TikTok: TikTokIcon,
  Website: WebsiteIcon,
};

export default function PlatformIcon({ platform, size = 20 }) {
  const Icon = ICONS[platform];
  return Icon ? <Icon size={size} /> : null;
}
