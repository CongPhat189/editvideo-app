import { Circle, Path, Rect } from 'react-native-svg';

import { Icon } from '@/components/AuthIcons';
import { colors } from '@/constants/theme';

const createIcon = (shapes) => {
  const HomeIcon = ({ color = colors.text, size = 24 }) => (
    <Icon color={color} size={size}>{shapes}</Icon>
  );
  return HomeIcon;
};

export const MenuIcon = createIcon(<Path d="M4 6h16M4 12h16M4 18h16" />);

export const CloseIcon = createIcon(<Path d="M18 6 6 18M6 6l12 12" />);

export const BackIcon = createIcon(<Path d="m15 18-6-6 6-6" />);

export const SendIcon = createIcon(<Path d="M12 19V5M5 12l7-7 7 7" />);

export const PlusIcon = createIcon(<Path d="M5 12h14M12 5v14" />);

export const PlayIcon = createIcon(
  <Path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z" />
);

export const CheckIcon = createIcon(<Path d="M20 6 9 17l-5-5" />);

export const CalendarIcon = createIcon(
  <>
    <Rect x={3} y={4} width={18} height={18} rx={2} />
    <Path d="M16 2v4M8 2v4M3 10h18" />
  </>
);

export const FolderIcon = createIcon(
  <Path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
);

export const ClockIcon = createIcon(
  <>
    <Circle cx={12} cy={12} r={10} />
    <Path d="M12 6v6l4 2" />
  </>
);

export const AgentIcon = createIcon(
  <>
    <Path d="M12 8V4H8" />
    <Path d="M6 8h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z" />
    <Path d="M2 14h2M20 14h2M15 13v2M9 13v2" />
  </>
);

export const MoreIcon = createIcon(
  <>
    <Circle cx={5} cy={12} r={1} />
    <Circle cx={12} cy={12} r={1} />
    <Circle cx={19} cy={12} r={1} />
  </>
);

export const ChatIcon = createIcon(<Path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />);

export const EditIcon = createIcon(
  <>
    <Path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
    <Path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z" />
  </>
);

export const SettingsIcon = createIcon(
  <>
    <Path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
    <Circle cx={12} cy={12} r={3} />
  </>
);

export const PencilIcon = createIcon(
  <>
    <Path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z" />
    <Path d="m15 5 4 4" />
  </>
);

export const ChevronRightIcon = createIcon(<Path d="m9 18 6-6-6-6" />);

export const SmileIcon = createIcon(
  <>
    <Circle cx={12} cy={12} r={10} />
    <Path d="M8 14s1.5 2 4 2 4-2 4-2" />
    <Path d="M9 9h.01M15 9h.01" />
  </>
);

export const BookIcon = createIcon(
  <>
    <Path d="M12 7v14" />
    <Path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z" />
  </>
);

export const PluginIcon = createIcon(
  <>
    <Circle cx={12} cy={12} r={4} />
    <Path d="M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-4 8" />
  </>
);

export const MailIcon = createIcon(
  <>
    <Path d="m22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7" />
    <Rect x={2} y={4} width={20} height={16} rx={2} />
  </>
);

export const PlanIcon = createIcon(
  <>
    <Rect x={3} y={3} width={18} height={18} rx={2} />
    <Path d="M8 12h8M12 8v8" />
  </>
);

export const RestoreIcon = createIcon(
  <>
    <Path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
    <Path d="M3 3v5h5" />
  </>
);

export const TrashIcon = createIcon(
  <>
    <Path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    <Path d="M10 11v6M14 11v6" />
  </>
);
