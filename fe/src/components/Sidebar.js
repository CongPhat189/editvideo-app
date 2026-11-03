import { router, useFocusEffect } from 'expo-router';
import { use, useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg';

import {
  AgentIcon,
  ChatIcon,
  ClockIcon,
  EditIcon,
  FolderIcon,
  MoreIcon,
  SettingsIcon,
} from '@/components/HomeIcons';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import { getProjects, getRecentProjectIds } from '@/services/projects';

const FOOTER_HEIGHT = 48;
const FOOTER_GAP = 12;
const FADE_HEIGHT = 96;
const SMALL_SCREEN = 360;
const UNTITLED = 'Cuộc trò chuyện chưa đặt tên';

// Không có href: chỉ đóng Sidebar
const NAV_ITEMS = [
  { key: 'projects', label: 'Dự án', Icon: FolderIcon, href: '/projects/new' },
  { key: 'scheduled', label: 'Đã lên lịch', Icon: ClockIcon, href: '/scheduled' },
  { key: 'agents', label: 'Agent', Icon: AgentIcon, href: '/agents' },
  { key: 'more', label: 'Thêm', Icon: MoreIcon },
];

const Row = ({ label, Icon, onPress }) => (
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

export default function Sidebar({ onClose }) {
  const [user] = use(MyUserContext);
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const isSmallScreen = width < SMALL_SCREEN;
  const [projects, setProjects] = useState([]);
  const [recentIds, setRecentIds] = useState([]);
  const token = user?.access_token;

  useFocusEffect(
    useCallback(() => {
      if (!token) return undefined;
      let active = true;
      Promise.all([getProjects(token), getRecentProjectIds(token)])
        .then(([projectItems, ids]) => {
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
    onClose();
    if (href) router.push(href);
  };

  return (
    <SafeAreaView style={styles.container} edges={['top', 'left']}>
      <View style={styles.header} />

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
            onPress={() => openPage(`/projects/${item.id}`)}
          />
        ))}

        {recents.length > 0 ? <Text style={styles.sectionTitle}>Gần đây</Text> : null}
        {recents.map((item) => (
          <Row key={item.id} label={item.title || UNTITLED} onPress={() => openPage(`/projects/${item.id}`)} />
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

      <View style={[styles.footer, isSmallScreen && styles.footerSmall, { bottom: footerSpace }]}>
        <Pressable
          onPress={onClose}
          style={({ pressed }) => [
            styles.chatButton,
            isSmallScreen && styles.chatButtonSmall,
            pressed && styles.pressed,
          ]}
          accessibilityRole="button"
          accessibilityLabel="Đoạn chat"
        >
          <EditIcon />
          <Text style={styles.chatButtonText} numberOfLines={1}>Đoạn chat</Text>
        </Pressable>
        <Pressable
          onPress={() => router.push('/settings')}
          style={({ pressed }) => [styles.settingsButton, pressed && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel="Cài đặt"
        >
          <SettingsIcon />
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.backgroundDeep,
  },
  header: {
    height: 56,
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
    justifyContent: 'space-between',
    gap: 12,
    paddingHorizontal: 24,
  },
  footerSmall: {
    paddingHorizontal: 12,
  },
  chatButton: {
    minHeight: FOOTER_HEIGHT,
    flexShrink: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 20,
    borderRadius: FOOTER_HEIGHT / 2,
    backgroundColor: colors.accent,
  },
  chatButtonSmall: {
    paddingHorizontal: 12,
  },
  chatButtonText: {
    flexShrink: 1,
    color: colors.text,
    fontSize: 17,
    fontWeight: '600',
  },
  settingsButton: {
    width: FOOTER_HEIGHT,
    height: FOOTER_HEIGHT,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: FOOTER_HEIGHT / 2,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.divider,
    backgroundColor: colors.background,
  },
});
