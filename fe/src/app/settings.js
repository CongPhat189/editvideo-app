import { router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PhoneIcon } from '@/components/AuthIcons';
import {
  BookIcon,
  ChevronRightIcon,
  CloseIcon,
  MailIcon,
  PencilIcon,
  PlanIcon,
  PluginIcon,
  RestoreIcon,
  SmileIcon,
} from '@/components/HomeIcons';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import useTopBarSpace from '@/hooks/useTopBarSpace';

const NO_DATA = 'Chưa có';
const PAGE_MAX_WIDTH = 560;
const PAGE_PADDING = 16;

// Bản mẫu giao diện: các mục chưa gắn chức năng
const CUSTOMIZE_ROWS = [
  { key: 'personalize', label: 'Cá nhân hóa', Icon: SmileIcon, chevron: true },
  { key: 'memory', label: 'Bộ nhớ', Icon: BookIcon, chevron: true },
  { key: 'plugin', label: 'Plugin', Icon: PluginIcon, chevron: true },
];

const getInitials = (name = '') => {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length > 1) return `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase();
  return (words[0] ?? '').slice(0, 2).toUpperCase();
};

const SettingsCard = ({ rows }) => (
  <View style={styles.card}>
    {rows.map(({ key, label, value, Icon, chevron }, index) => (
      <Pressable
        key={key}
        style={({ pressed }) => [styles.row, pressed && styles.pressed]}
        accessibilityRole="button"
        accessibilityLabel={value ? `${label}: ${value}` : label}
      >
        <Icon size={22} color={colors.text} />
        <View style={[styles.rowBody, index > 0 && styles.rowDivider]}>
          <Text style={styles.rowLabel} numberOfLines={1}>{label}</Text>
          {value ? <Text style={styles.rowValue} numberOfLines={1}>{value}</Text> : null}
          {chevron ? <ChevronRightIcon size={20} color={colors.textSecondary} /> : null}
        </View>
      </Pressable>
    ))}
  </View>
);

export default function Settings() {
  const [user] = use(MyUserContext);
  const topBarSpace = useTopBarSpace();

  const close = () => {
    if (router.canGoBack()) router.back();
    else router.replace('/');
  };

  const accountRows = [
    { key: 'email', label: 'Email', value: NO_DATA, Icon: MailIcon, chevron: true },
    { key: 'phone', label: 'Số điện thoại', value: user?.phone, Icon: PhoneIcon },
    { key: 'plan', label: 'Gói đăng ký', value: NO_DATA, Icon: PlanIcon },
    { key: 'restore', label: 'Khôi phục mua hàng', Icon: RestoreIcon },
  ];

  return (
    <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
      <StatusBar style="light" />
      <View style={[styles.header, { paddingTop: topBarSpace }]}>
        <Pressable
          onPress={close}
          hitSlop={2}
          style={({ pressed }) => [styles.closeButton, pressed && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel="Đóng"
        >
          <CloseIcon />
        </Pressable>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.page}>
          <View style={styles.profile}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{getInitials(user?.full_name)}</Text>
              <Pressable
                hitSlop={8}
                style={({ pressed }) => [styles.avatarBadge, pressed && styles.pressedBadge]}
                accessibilityRole="button"
                accessibilityLabel="Đổi ảnh đại diện"
              >
                <PencilIcon size={16} />
              </Pressable>
            </View>
            <Text style={styles.name} numberOfLines={1}>{user?.full_name}</Text>
          </View>

          <View style={styles.upgradeCard}>
            <View style={styles.upgradeText}>
              <Text style={styles.upgradeTitle}>Làm được nhiều hơn</Text>
              <Text style={styles.upgradeBody}>
                Trải nghiệm hạn mức cao hơn và quyền truy cập vào các tính năng nâng cao.
              </Text>
            </View>
            <Pressable
              style={({ pressed }) => [styles.upgradeButton, pressed && styles.pressed]}
              accessibilityRole="button"
            >
              <Text style={styles.upgradeButtonText}>Nâng cấp</Text>
            </Pressable>
          </View>

          <Text style={styles.sectionTitle}>Tùy chỉnh</Text>
          <SettingsCard rows={CUSTOMIZE_ROWS} />

          <Text style={styles.sectionTitle}>Tài khoản</Text>
          <SettingsCard rows={accountRows} />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.backgroundDeep,
  },
  header: {
    width: '100%',
    maxWidth: PAGE_MAX_WIDTH + PAGE_PADDING * 2,
    alignSelf: 'center',
    flexDirection: 'row',
    justifyContent: 'flex-end',
    paddingHorizontal: PAGE_PADDING,
    paddingBottom: 8,
  },
  closeButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 22,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.divider,
    backgroundColor: colors.background,
  },
  pressed: {
    opacity: 0.7,
  },
  pressedBadge: {
    opacity: 0.85,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: PAGE_PADDING,
    paddingBottom: 40,
  },
  page: {
    width: '100%',
    maxWidth: PAGE_MAX_WIDTH,
    alignSelf: 'center',
  },
  profile: {
    alignItems: 'center',
    marginBottom: 24,
  },
  avatar: {
    width: 72,
    height: 72,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 36,
    backgroundColor: colors.avatar,
  },
  avatarText: {
    color: colors.text,
    fontSize: 28,
  },
  avatarBadge: {
    position: 'absolute',
    right: -4,
    bottom: -4,
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 16,
    backgroundColor: colors.surface,
  },
  name: {
    color: colors.text,
    fontSize: 17,
    fontWeight: '600',
    marginTop: 12,
  },
  upgradeCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 24,
    borderRadius: 20,
    backgroundColor: colors.background,
  },
  upgradeText: {
    flex: 1,
  },
  upgradeTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '500',
  },
  upgradeBody: {
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 20,
    marginTop: 4,
  },
  upgradeButton: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
    borderRadius: 22,
    backgroundColor: colors.primary,
  },
  upgradeButtonText: {
    color: colors.onPrimary,
    fontSize: 16,
    fontWeight: '500',
  },
  sectionTitle: {
    color: colors.textSecondary,
    fontSize: 17,
    fontWeight: '600',
    marginTop: 32,
    marginBottom: 12,
    paddingHorizontal: 16,
  },
  card: {
    paddingHorizontal: 16,
    borderRadius: 20,
    backgroundColor: colors.background,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  rowBody: {
    flex: 1,
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 8,
  },
  rowDivider: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.divider,
  },
  rowLabel: {
    flex: 1,
    color: colors.text,
    fontSize: 17,
  },
  rowValue: {
    flexShrink: 1,
    color: colors.textSecondary,
    fontSize: 17,
  },
});
