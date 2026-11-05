import { Circle, Path, Rect } from 'react-native-svg';

import { Icon } from '@/components/AuthIcons';
import { useThemeColors } from '@/constants/theme';

// shapes: các nét vẽ; accent: lớp phủ màu nhạt bên dưới (tùy chọn)
const createIcon = (shapes, accent = null, strokeWidth) => {
  const HomeIcon = ({ color, size = 24 }) => {
    const colors = useThemeColors();
    return (
      <Icon color={color ?? colors.text} size={size} accent={accent} strokeWidth={strokeWidth}>
        {shapes}
      </Icon>
    );
  };
  return HomeIcon;
};

// Điều hướng & thao tác cơ bản: chỉ nét, gọn và mảnh
export const MenuIcon = createIcon(<Path d="M4 7h16M4 12h10M4 17h16" />, null, 1.7);

export const CloseIcon = createIcon(<Path d="M17.5 6.5l-11 11M6.5 6.5l11 11" />);

export const BackIcon = createIcon(<Path d="m14.5 18-6-6 6-6" />, null, 1.8);

export const ChevronRightIcon = createIcon(<Path d="m9.5 18 6-6-6-6" />, null, 1.8);

export const SendIcon = createIcon(<Path d="M12 19V5.5M6 11.5l6-6 6 6" />, null, 2);

export const PlusIcon = createIcon(<Path d="M12 5v14M5 12h14" />, null, 1.7);

export const CheckIcon = createIcon(<Path d="m5 12.5 4.5 4.5L19 7.5" />, null, 2);

export const StopIcon = createIcon(
  <Rect x={6} y={6} width={12} height={12} rx={2.5} />,
  <Rect x={6} y={6} width={12} height={12} rx={2.5} />
);

export const MoreIcon = createIcon(
  <>
    <Circle cx={5.5} cy={12} r={1.2} />
    <Circle cx={12} cy={12} r={1.2} />
    <Circle cx={18.5} cy={12} r={1.2} />
  </>,
  null,
  2
);

// Icon nội dung: duotone với lớp phủ vàng nhạt
export const MicIcon = createIcon(
  <>
    <Rect x={9} y={2.5} width={6} height={12} rx={3} />
    <Path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M9 21h6" />
  </>,
  <Rect x={9} y={2.5} width={6} height={12} rx={3} />
);

export const PlayIcon = createIcon(
  <Path d="M6.5 5.2a1.6 1.6 0 0 1 2.42-1.37l10.2 6.4a2 2 0 0 1 0 3.4l-10.2 6.4A1.6 1.6 0 0 1 6.5 18.8z" />,
  <Path d="M6.5 5.2a1.6 1.6 0 0 1 2.42-1.37l10.2 6.4a2 2 0 0 1 0 3.4l-10.2 6.4A1.6 1.6 0 0 1 6.5 18.8z" />
);

export const CalendarIcon = createIcon(
  <>
    <Rect x={3} y={4.5} width={18} height={16.5} rx={3} />
    <Path d="M8 2.5v4M16 2.5v4M3 10h18" />
    <Path d="M8 14h.01M12 14h.01M16 14h.01M8 17.5h.01M12 17.5h.01" strokeWidth={2.2} />
  </>,
  <Path d="M3 7.5a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3V10H3z" />
);

// Bảng clapper điện ảnh: biểu tượng cho dự án video
export const ClapperIcon = createIcon(
  <>
    <Path d="M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    <Path d="M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.5l13.5-4c1.1-.3 2.2.3 2.5 1.3z" />
    <Path d="m6.2 5.3 3.1 3.9M12.4 3.4l3.1 4" />
  </>,
  <Path d="M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
);

export const FolderIcon = createIcon(
  <Path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />,
  <Path d="M22 10v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-8z" />
);

export const ClockIcon = createIcon(
  <>
    <Circle cx={12} cy={12} r={9.5} />
    <Path d="M12 7v5l3.2 2" />
  </>,
  <Circle cx={12} cy={12} r={9.5} />
);

// Ngôi sao lấp lánh: biểu tượng Agent AI
export const AgentIcon = createIcon(
  <>
    <Path d="M10.4 3.6a.65.65 0 0 1 1.2 0l1.36 3.67a4 4 0 0 0 2.37 2.37l3.67 1.36a.65.65 0 0 1 0 1.2l-3.67 1.36a4 4 0 0 0-2.37 2.37l-1.36 3.67a.65.65 0 0 1-1.2 0l-1.36-3.67a4 4 0 0 0-2.37-2.37L3.6 12.2a.65.65 0 0 1 0-1.2l3.67-1.36a4 4 0 0 0 2.37-2.37z" />
    <Path d="M19 2.5v4M21 4.5h-4M18.5 17.5v3M20 19h-3" />
  </>,
  <Path d="M10.4 3.6a.65.65 0 0 1 1.2 0l1.36 3.67a4 4 0 0 0 2.37 2.37l3.67 1.36a.65.65 0 0 1 0 1.2l-3.67 1.36a4 4 0 0 0-2.37 2.37l-1.36 3.67a.65.65 0 0 1-1.2 0l-1.36-3.67a4 4 0 0 0-2.37-2.37L3.6 12.2a.65.65 0 0 1 0-1.2l3.67-1.36a4 4 0 0 0 2.37-2.37z" />
);

export const ChatIcon = createIcon(
  <Path d="M7.9 20A9 9 0 1 0 4 16.1L2.5 21.5z" />,
  <Path d="M7.9 20A9 9 0 1 0 4 16.1L2.5 21.5z" />
);

export const EditIcon = createIcon(
  <>
    <Path d="M12 3.5H6a2.5 2.5 0 0 0-2.5 2.5v12A2.5 2.5 0 0 0 6 20.5h12a2.5 2.5 0 0 0 2.5-2.5v-6" />
    <Path d="M18.4 2.6a1.9 1.9 0 0 1 2.7 2.7l-8.6 8.6a2 2 0 0 1-.85.5l-2.9.85a.5.5 0 0 1-.6-.6l.85-2.9a2 2 0 0 1 .5-.85z" />
  </>,
  <Path d="M18.4 2.6a1.9 1.9 0 0 1 2.7 2.7l-8.6 8.6a2 2 0 0 1-.85.5l-2.9.85a.5.5 0 0 1-.6-.6l.85-2.9a2 2 0 0 1 .5-.85z" />
);

export const PencilIcon = createIcon(
  <>
    <Path d="M21.17 6.81a2.82 2.82 0 0 0-3.99-3.99L3.84 16.17a2 2 0 0 0-.5.83l-1.32 4.35a.5.5 0 0 0 .62.62l4.35-1.32a2 2 0 0 0 .83-.5z" />
    <Path d="m15 5 4 4" />
  </>,
  <Path d="M21.17 6.81a2.82 2.82 0 0 0-3.99-3.99L3.84 16.17a2 2 0 0 0-.5.83l-1.32 4.35a.5.5 0 0 0 .62.62l4.35-1.32a2 2 0 0 0 .83-.5z" />
);

export const SettingsIcon = createIcon(
  <>
    <Path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
    <Circle cx={12} cy={12} r={3} />
  </>,
  <Circle cx={12} cy={12} r={3} />
);

export const ProfileIcon = createIcon(
  <>
    <Circle cx={12} cy={8} r={4} />
    <Path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
  </>,
  <>
    <Circle cx={12} cy={8} r={4} />
    <Path d="M4.5 21a7.5 7.5 0 0 1 15 0z" />
  </>
);

export const LogoutIcon = createIcon(
  <>
    <Path d="M14 3.5h4a2.5 2.5 0 0 1 2.5 2.5v12a2.5 2.5 0 0 1-2.5 2.5h-4" />
    <Path d="M9.5 16.5 5 12l4.5-4.5M5 12h10.5" />
  </>,
  <Path d="M14 3.5h4a2.5 2.5 0 0 1 2.5 2.5v12a2.5 2.5 0 0 1-2.5 2.5h-4z" />
);

export const SmileIcon = createIcon(
  <>
    <Circle cx={12} cy={12} r={9.5} />
    <Path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01" />
  </>,
  <Circle cx={12} cy={12} r={9.5} />
);

export const BookIcon = createIcon(
  <>
    <Path d="M12 7v14" />
    <Path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z" />
  </>,
  <Path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z" />
);

// Quả địa cầu: biểu tượng domain máy chủ
export const PluginIcon = createIcon(
  <>
    <Circle cx={12} cy={12} r={9.5} />
    <Path d="M12 2.5a14 14 0 0 0 0 19 14 14 0 0 0 0-19M2.5 12h19" />
  </>,
  <Circle cx={12} cy={12} r={9.5} />
);

export const MailIcon = createIcon(
  <>
    <Rect x={2.5} y={4.5} width={19} height={15} rx={2.5} />
    <Path d="m21.5 7.5-8.5 5.4a2 2 0 0 1-2 0L2.5 7.5" />
  </>,
  <Rect x={2.5} y={4.5} width={19} height={15} rx={2.5} />
);

// Lịch có dấu cộng: lập lịch nội dung
export const PlanIcon = createIcon(
  <>
    <Rect x={3} y={4.5} width={18} height={16.5} rx={3} />
    <Path d="M8 2.5v4M16 2.5v4M3 10h18M12 13.5v4.5M9.75 15.75h4.5" />
  </>,
  <Path d="M3 7.5a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3V10H3z" />
);

// Bóng đèn: lên ý tưởng
export const IdeaIcon = createIcon(
  <>
    <Path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5" />
    <Path d="M9 18h6M10 21.5h4" />
  </>,
  <Path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5z" />
);

// Trang giấy có chữ: kịch bản
export const ScriptIcon = createIcon(
  <>
    <Path d="M14.5 2.5H6.5a2.5 2.5 0 0 0-2.5 2.5v14a2.5 2.5 0 0 0 2.5 2.5h11a2.5 2.5 0 0 0 2.5-2.5V8z" />
    <Path d="M14 2.5V7a1.5 1.5 0 0 0 1.5 1.5H20M8.5 13h7M8.5 17h5" />
  </>,
  <Path d="M14.5 2.5H6.5a2.5 2.5 0 0 0-2.5 2.5v14a2.5 2.5 0 0 0 2.5 2.5h11a2.5 2.5 0 0 0 2.5-2.5V8z" />
);

export const RestoreIcon = createIcon(
  <>
    <Path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
    <Path d="M3 3v5h5" />
  </>
);

export const TrashIcon = createIcon(
  <>
    <Path d="M3.5 6h17M18.5 6v13.5a2.5 2.5 0 0 1-2.5 2.5H8a2.5 2.5 0 0 1-2.5-2.5V6m3 0V4.5A2 2 0 0 1 10.5 2.5h3a2 2 0 0 1 2 2V6" />
    <Path d="M10 11v6M14 11v6" />
  </>,
  <Path d="M5.5 6h13v13.5a2.5 2.5 0 0 1-2.5 2.5H8a2.5 2.5 0 0 1-2.5-2.5z" />
);
