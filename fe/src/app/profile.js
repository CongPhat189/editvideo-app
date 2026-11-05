import { router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { BackIcon, ProfileIcon } from '@/components/HomeIcons';
import { MyUserContext } from '@/config/Contexts';
import { useThemeColors, useThemeStyles } from '@/constants/theme';

const getInitials = (name = '') => name.trim().split(/\s+/).filter(Boolean).map((part) => part[0]).slice(-2).join('').toUpperCase() || 'U';

export default function Profile() {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);
  const [user] = use(MyUserContext);
  const insets = useSafeAreaInsets();

  const goBack = () => {
    if (router.canGoBack()) router.back();
    else router.replace('/');
  };

  const details = [
    { label: 'Họ và tên', value: user?.full_name },
    { label: 'Số điện thoại', value: user?.phone },
    ...(user?.email ? [{ label: 'Email', value: user.email }] : []),
  ].filter((item) => item.value);

  return (
    <View style={[styles.container, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <StatusBar style={colors.backgroundDeep === '#000000' ? 'light' : 'dark'} />
      <View style={styles.header}>
        <Pressable
          onPress={goBack}
          style={({ pressed }) => [styles.backButton, pressed && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel="Quay lại"
        >
          <BackIcon size={22} />
        </Pressable>
        <Text style={styles.title}>Hồ sơ</Text>
        <View style={styles.headerSpacer} />
      </View>

      <View style={styles.content}>
        <View style={styles.identity}>
          <View style={styles.avatar}><Text style={styles.avatarText}>{getInitials(user?.full_name || '')}</Text></View>
          <Text style={styles.name}>{user?.full_name || 'Người dùng'}</Text>
          <Text style={styles.plan}>Free</Text>
        </View>
        <View style={styles.card}>
          {details.map(({ label, value }, index) => (
            <View key={label} style={[styles.detailRow, index > 0 && styles.divided]}>
              <Text style={styles.label}>{label}</Text>
              <Text style={styles.value}>{value}</Text>
            </View>
          ))}
          {details.length === 0 ? <Text style={styles.empty}>Chưa có thông tin hồ sơ.</Text> : null}
        </View>
        <View style={styles.note}>
          <ProfileIcon size={18} color={colors.textSecondary} />
          <Text style={styles.noteText}>Thông tin hồ sơ của tài khoản đang đăng nhập.</Text>
        </View>
      </View>
    </View>
  );
}

const createStyles = (colors) => StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.backgroundDeep },
  header: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.divider,
  },
  backButton: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center', borderRadius: 20 },
  title: { color: colors.text, fontSize: 17, fontWeight: '600' },
  headerSpacer: { width: 40 },
  content: { width: '100%', maxWidth: 560, alignSelf: 'center', padding: 20 },
  identity: { alignItems: 'center', paddingVertical: 24 },
  avatar: {
    width: 76,
    height: 76,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 38,
    backgroundColor: colors.avatar,
  },
  avatarText: { color: '#FFFFFF', fontSize: 24, fontWeight: '600' },
  name: { color: colors.text, fontSize: 20, fontWeight: '600', marginTop: 12 },
  plan: { color: colors.textSecondary, fontSize: 13, marginTop: 4 },
  card: { paddingHorizontal: 16, borderRadius: 16, backgroundColor: colors.background },
  detailRow: { minHeight: 58, justifyContent: 'center', gap: 4 },
  divided: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.divider },
  label: { color: colors.textSecondary, fontSize: 12 },
  value: { color: colors.text, fontSize: 15 },
  empty: { color: colors.textSecondary, fontSize: 14, paddingVertical: 18 },
  note: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 16, paddingHorizontal: 4 },
  noteText: { flex: 1, color: colors.textSecondary, fontSize: 13 },
  pressed: { opacity: 0.7 },
});
