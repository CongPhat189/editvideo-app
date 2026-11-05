import { useSafeAreaInsets } from 'react-native-safe-area-context';

const MIN_DISTANCE_FROM_TOP = 16;
const MIN_PADDING = 4;

// Nút tròn trên cùng luôn cách mép trên ít nhất 16, bằng khoảng cách với mép bên, kể cả máy không có tai thỏ
export default function useTopBarSpace() {
  const { top } = useSafeAreaInsets();
  return Math.max(MIN_PADDING, MIN_DISTANCE_FROM_TOP - top);
}
