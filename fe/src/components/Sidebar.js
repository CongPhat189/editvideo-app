import { router, useFocusEffect } from 'expo-router';
import { use, useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg';

import {
  AgentIcon,
  ChatIcon,
  ChevronRightIcon,
  ClockIcon,
  MoreIcon,
  PencilIcon,
  ProfileIcon,
  LogoutIcon,
  SettingsIcon,
} from '@/components/HomeIcons';
import { MyUserContext } from '@/config/Contexts';
import { useThemeColors, useThemeStyles } from '@/constants/theme';
import { getProjects, getRecentProjectIds } from '@/services/projects';

const FOOTER_HEIGHT = 58;
const FOOTER_GAP = 12;
const FADE_HEIGHT = 96;
const UNTITLED = 'Cuộc trò chuyện chưa đặt tên';

// Giữ danh sách lần tải trước để Sidebar của màn hình mới hiện ngay, không bị trống rồi mới hiện lại
let cache = { token: null, projects: [], recentIds: [] };

// Không có href: chỉ đóng Sidebar
const NAV_ITEMS = [
  { key: 'projects', label: 'Cuộc trò chuyện mới', Icon: PencilIcon, href: '/projects/new' },
  { key: 'scheduled', label: 'Đã lên lịch', Icon: ClockIcon, href: '/scheduled' },
  { key: 'agents', label: 'Agent', Icon: AgentIcon, href: '/agents' },
  { key: 'more', label: 'Thêm', Icon: MoreIcon },
];

const Row = ({ label, Icon, onPress }) => {
  const styles = useThemeStyles(createStyles);
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      {Icon ? <Icon /> : null}
      <Text style={styles.rowLabel} numberOfLines={1}>{label}</Text>
    </Pressable>
  );
};

export default function Sidebar({ onClose, onNavigate }) {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

  const [user, dispatch] = use(MyUserContext);
  const insets = useSafeAreaInsets();
  const token = user?.access_token;
  const cached = cache.token === token ? cache : { projects: [], recentIds: [] };
  const [projects, setProjects] = useState(cached.projects);
  const [recentIds, setRecentIds] = useState(cached.recentIds);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);

  useFocusEffect(
    useCallback(() => {
      if (!token) return undefined;
      let active = true;
      Promise.all([getProjects(token), getRecentProjectIds(token)])
        .then(([projectItems, ids]) => {
          cache = { token, projects: projectItems, recentIds: ids };
          if (!active) return;
          setProjects(projectItems);
          setRecentIds(ids);
        })
        .catch(() => {});
      return () => {
        active = false;
      };
    }, [token])
  );

  const pinned = projects.filter((item) => item.pinned_at);
  // Thứ tự theo lần mở gần nhất; dự án đã xóa hoặc lưu trữ thì không hiện
  const recents = recentIds.map((id) => projects.find((item) => item.id === id)).filter(Boolean);
  const footerSpace = insets.bottom + FOOTER_GAP;

  const openPage = (href) => {
    setAccountMenuOpen(false);
    if (href) onNavigate(href);
    else onClose();
  };

  const logout = () => {
    setAccountMenuOpen(false);
    dispatch({ type: 'LOGOUT' });
    router.replace('/login');
  };
  const initials = (user?.full_name || 'U').trim().split(/\s+/).map((part) => part[0]).slice(-2).join('').toUpperCase();

  return (
    <SafeAreaView style={styles.container} edges={['top', 'left']}>
      <View style={styles.header}>
        <Text style={styles.logo} accessibilityRole="header">AI EDIT</Text>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={{ paddingBottom: footerSpace + FOOTER_HEIGHT + FOOTER_GAP }}
        showsVerticalScrollIndicator={false}
      >
        {NAV_ITEMS.map(({ key, label, Icon, href }) => (
          <Row key={key} label={label} Icon={Icon} onPress={() => openPage(href)} />
        ))}

        {pinned.length > 0 ? <Text style={styles.sectionTitle}>Đã ghim</Text> : null}
        {pinned.map((item) => (
          <Row
            key={item.id}
            label={item.title || UNTITLED}
            Icon={ChatIcon}
            onPress={() => onNavigate(`/projects/${item.id}`)}
          />
        ))}

        {recents.length > 0 ? <Text style={styles.sectionTitle}>Gần đây</Text> : null}
        {recents.map((item) => (
          <Row key={item.id} label={item.title || UNTITLED} onPress={() => onNavigate(`/projects/${item.id}`)} />
        ))}
      </ScrollView>

      <Svg
        style={styles.fade}
        width="100%"
        height={footerSpace + FADE_HEIGHT}
        pointerEvents="none"
      >
        <Defs>
          <LinearGradient id="sidebarFade" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor={colors.backgroundDeep} stopOpacity="0" />
            <Stop offset="0.7" stopColor={colors.backgroundDeep} stopOpacity="1" />
          </LinearGradient>
        </Defs>
        <Rect width="100%" height="100%" fill="url(#sidebarFade)" />
      </Svg>

      {accountMenuOpen ? (
        <>
          <Pressable
            style={styles.menuBackdrop}
            onPress={() => setAccountMenuOpen(false)}
            accessibilityRole="button"
            accessibilityLabel="Đóng menu tài khoản"
          />
          <View style={[styles.accountMenu, { bottom: footerSpace + FOOTER_HEIGHT + 8 }]}>
            <Pressable
              onPress={() => openPage('/profile')}
              style={({ pressed }) => [styles.accountSummary, pressed && styles.pressed]}
              accessibilityRole="button"
              accessibilityLabel="Mở hồ sơ"
            >
              <View style={styles.avatar}><Text style={styles.avatarText}>{initials}</Text></View>
              <View style={styles.accountCopy}>
                <Text style={styles.accountName} numberOfLines={1}>{user?.full_name || 'Tài khoản'}</Text>
                <Text style={styles.accountPlan}>Free</Text>
              </View>
              <ChevronRightIcon size={18} color={colors.textSecondary} />
            </Pressable>
            <View style={styles.menuDivider} />
            <Row label="Hồ sơ" Icon={ProfileIcon} onPress={() => openPage('/profile')} />
            <Row label="Cài đặt" Icon={SettingsIcon} onPress={() => openPage('/settings')} />
            <View style={styles.menuDivider} />
            <Row label="Đăng xuất" Icon={LogoutIcon} onPress={logout} />
          </View>
        </>
      ) : null}

      <View style={[styles.footer, { bottom: footerSpace }]}>
        <Pressable
          onPress={() => setAccountMenuOpen((open) => !open)}
          style={({ pressed }) => [styles.accountButton, accountMenuOpen && styles.accountButtonOpen, pressed && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel="Tài khoản"
          accessibilityState={{ expanded: accountMenuOpen }}
        >
          <View style={styles.avatar}><Text style={styles.avatarText}>{initials}</Text></View>
          <View style={styles.accountCopy}>
            <Text style={styles.accountName} numberOfLines={1}>{user?.full_name || 'Tài khoản'}</Text>
            <Text style={styles.accountPlan}>Free</Text>
          </View>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const createStyles = (colors) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.backgroundDeep,
  },
  header: {
    height: 56,
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  logo: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  pressed: {
    opacity: 0.7,
  },
  scroll: {
    flex: 1,
  },
  row: {
    minHeight: 48,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 24,
    paddingVertical: 8,
  },
  rowLabel: {
    flex: 1,
    color: colors.text,
    fontSize: 17,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 17,
    fontWeight: '600',
    marginTop: 24,
    marginBottom: 12,
    paddingHorizontal: 24,
  },
  fade: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
  },
  footer: {
    position: 'absolute',
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 8,
  },
  accountButton: {
    minHeight: 58,
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 10,
    borderRadius: 14,
    backgroundColor: colors.surface,
  },
  accountButtonOpen: {
    backgroundColor: colors.surfaceRaised,
  },
  avatar: {
    width: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
    backgroundColor: colors.avatar,
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '600',
  },
  accountCopy: {
    flex: 1,
  },
  accountName: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '500',
  },
  accountPlan: {
    color: colors.textSecondary,
    fontSize: 12,
    marginTop: 1,
  },
  menuBackdrop: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 2,
  },
  accountMenu: {
    position: 'absolute',
    left: 8,
    right: 8,
    zIndex: 3,
    paddingHorizontal: 8,
    paddingVertical: 8,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.divider,
    backgroundColor: colors.backgroundDeep,
    shadowColor: '#000000',
    shadowOpacity: 0.16,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 5 },
    elevation: 8,
  },
  accountSummary: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 8,
    borderRadius: 10,
  },
  menuDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.divider,
    marginVertical: 7,
    marginHorizontal: 8,
  },
});
