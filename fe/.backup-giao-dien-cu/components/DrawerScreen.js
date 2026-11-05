import { router, useLocalSearchParams, usePathname } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Keyboard } from 'react-native';

import MenuButton from '@/components/MenuButton';
import PushDrawer from '@/components/PushDrawer';
import Sidebar from '@/components/Sidebar';

const CLOSE_AFTER_PAGE_OPENS = 300;

// Khung chung của các trang mở từ Sidebar: bấm một mục thì Sidebar khép lại và nội dung trang đó trượt vào.
// root: Trang chủ giữ lại trong stack, các trang khác thay thế nhau để stack không dài thêm.
export default function DrawerScreen({ root = false, children }) {
  const { fromDrawer } = useLocalSearchParams();
  const pathname = usePathname();
  const [open, setOpen] = useState(fromDrawer === '1');
  const close = useCallback(() => setOpen(false), []);

  // Mở từ Sidebar: bắt đầu ở tư thế Sidebar đang mở rồi khép lại
  useEffect(() => {
    if (!open) return undefined;
    const frame = requestAnimationFrame(close);
    return () => cancelAnimationFrame(frame);
  }, []);

  const openMenu = () => {
    Keyboard.dismiss();
    setOpen(true);
  };

  const navigate = (href) => {
    if (href === pathname) {
      close();
      return;
    }
    const target = { pathname: href, params: { fromDrawer: '1' } };
    if (root) {
      router.push(target);
      // Khép khi trang mới đã che Trang chủ, để lúc quay về Sidebar ở đây không còn mở
      setTimeout(close, CLOSE_AFTER_PAGE_OPENS);
    } else {
      router.replace(target);
    }
  };

  return (
    <PushDrawer
      open={open}
      onClose={close}
      drawer={<Sidebar onClose={close} onNavigate={navigate} />}
    >
      {children(<MenuButton expanded={open} onPress={openMenu} />)}
    </PushDrawer>
  );
}
