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
  EditIcon,
  ProfileIcon,
  LogoutIcon,
  SettingsIcon,
} from '@/components/HomeIcons';
import { BrandMark } from '@/components/Luxe';
import { FadeIn, stagger } from '@/components/Motion';
import { MyUserContext } from '@/config/Contexts';
import { fonts, useThemeColors, useThemeStyles } from '@/constants/theme';
import { getProjects, getRecentProjectIds } from '@/services/projects';

const FOOTER_HEIGHT = 58;
const FOOTER_GAP = 12;
const FADE_HEIGHT = 96;
const UNTITLED = 'Cuộc trò chuyện chưa đặt tên';

// Giữ danh sách lần tải trước để Sidebar của màn hình mới hiện ngay, không bị trống rồi mới hiện lại
let cache = { token: null, projects: [], recentIds: [] };

// Không có href: chỉ đóng Sidebar
const NAV_ITEMS = [
  { key: 'projects', label: 'Cuộc trò chuyện mới', Icon: EditIcon, href: '/projects/new' },
  { key: 'scheduled', label: 'Đã lên lịch', Icon: ClockIcon, href: '/scheduled' },
  { key: 'agents', label: 'Agent', Icon: AgentIcon, href: '/agents' },
  { key: 'more', label: 'Thêm', Icon: MoreIcon },
];

const Row = ({ label, Icon, onPress, muted = false, delay = 0 }) => {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);
  return (
    <FadeIn axis="x" distance={-18} delay={delay} duration={480}>
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      {Icon ? (
        <View style={styles.rowIcon}><Icon size={18} color={colors.textSecondary} /></View>
      ) : (
        <View style={styles.rowBullet} />
      )}
      <Text style={[styles.rowLabel, muted && styles.rowLabelMuted]} numberOfLines={1}>{label}</Text>
    </Pressable>
    </FadeIn>
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
        <BrandMark size={34} shimmer />
        <View>
          <Text style={styles.logo} accessibilityRole="header">AI EDIT</Text>
          <Text style={styles.logoTagline}>Video Studio</Text>
        </View>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={{ paddingBottom: footerSpace + FOOTER_HEIGHT + FOOTER_GAP }}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.navGroup}>
          {NAV_ITEMS.map(({ key, label, Icon, href }, index) => (
            <Row key={key} label={label} Icon={Icon} delay={stagger(index, 50, 80)} onPress={() => openPage(href)} />
          ))}
        </View>

        {pinned.length > 0 ? <Text style={styles.sectionTitle}>Đã ghim</Text> : null}
        {pinned.map((item, index) => (
          <Row
            key={item.id}
            delay={stagger(index, 40, 260)}
            label={item.title || UNTITLED}
            Icon={ChatIcon}
            onPress={() => onNavigate(`/projects/${item.id}`)}
          />
        ))}

        {recents.length > 0 ? <Text style={styles.sectionTitle}>Gần đây</Text> : null}
        {recents.map((item, index) => (
          <Row key={item.id} label={item.title || UNTITLED} muted delay={stagger(index, 40, 320)} onPress={() => onNavigate(`/projects/${item.id}`)} />
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
          <FadeIn style={[styles.accountMenu, { bottom: footerSpace + FOOTER_HEIGHT + 8 }]} distance={12} duration={320}>
            <Pressable
              onPress={() => openPage('/profile')}
              style={({ pressed }) => [styles.accountSummary, pressed && styles.pressed]}
              accessibilityRole="button"
              accessibilityLabel="Mở hồ sơ"
            >
              <View style={styles.avatar}><Text style={styles.avatarText}>{initials}</Text></View>
              <View style={styles.accountCopy}>
                <Text style={styles.accountName} numberOfLines={1}>{user?.full_name || 'Tài khoản'}</Text>
                <View style={styles.planBadge}><Text style={styles.accountPlan}>Free</Text></View>
              </View>
              <ChevronRightIcon size={18} color={colors.textMuted} />
            </Pressable>
            <View style={styles.menuDivider} />
            <Row label="Hồ sơ" Icon={ProfileIcon} onPress={() => openPage('/profile')} />
            <Row label="Cài đặt" Icon={SettingsIcon} onPress={() => openPage('/settings')} />
            <View style={styles.menuDivider} />
            <Row label="Đăng xuất" Icon={LogoutIcon} onPress={logout} />
          </FadeIn>
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
            <View style={styles.planBadge}><Text style={styles.accountPlan}>Free</Text></View>
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
    height: 68,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 20,
  },
  logo: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 18,
    fontWeight: '700',
    letterSpacing: 2.2,
  },
  logoTagline: {
    color: colors.gold,
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 1.8,
    textTransform: 'uppercase',
    marginTop: 1,
  },
  pressed: {
    opacity: 0.7,
  },
  scroll: {
    flex: 1,
  },
  navGroup: {
    marginHorizontal: 12,
    marginTop: 6,
    paddingVertical: 6,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    backgroundColor: colors.card,
  },
  row: {
    minHeight: 46,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginHorizontal: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  rowPressed: {
    backgroundColor: colors.goldSoft,
  },
  rowIcon: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  rowBullet: {
    width: 5,
    height: 5,
    borderRadius: 3,
    marginHorizontal: 13.5,
    backgroundColor: colors.goldBorder,
  },
  rowLabel: {
    flex: 1,
    color: colors.text,
    fontSize: 15.5,
    fontWeight: '500',
  },
  rowLabelMuted: {
    color: colors.textSecondary,
    fontWeight: '400',
  },
  sectionTitle: {
    color: colors.gold,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 2,
    textTransform: 'uppercase',
    marginTop: 28,
    marginBottom: 8,
    paddingHorizontal: 30,
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
    paddingHorizontal: 12,
  },
  accountButton: {
    minHeight: 58,
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 12,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
  },
  accountButtonOpen: {
    borderColor: colors.goldBorder,
    backgroundColor: colors.surfaceRaised,
  },
  avatar: {
    width: 34,
    height: 34,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 17,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.avatar,
  },
  avatarText: {
    color: colors.onAvatar,
    fontSize: 12.5,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  accountCopy: {
    flex: 1,
    alignItems: 'flex-start',
  },
  accountName: {
    color: colors.text,
    fontSize: 14.5,
    fontWeight: '600',
  },
  planBadge: {
    marginTop: 3,
    paddingHorizontal: 7,
    paddingVertical: 1,
    borderRadius: 6,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
  },
  accountPlan: {
    color: colors.gold,
    fontSize: 10.5,
    fontWeight: '700',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  menuBackdrop: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 2,
  },
  accountMenu: {
    position: 'absolute',
    left: 12,
    right: 12,
    zIndex: 3,
    paddingHorizontal: 6,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
    shadowColor: colors.shadow,
    shadowOpacity: 0.35,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 10 },
    elevation: 12,
  },
  accountSummary: {
    minHeight: 60,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 12,
    borderRadius: 14,
  },
  menuDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.borderStrong,
    marginVertical: 6,
    marginHorizontal: 12,
  },
});
