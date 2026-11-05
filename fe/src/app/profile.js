import { router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { BackIcon, ProfileIcon } from '@/components/HomeIcons';
import { AmbientGlow } from '@/components/Luxe';
import { Breathing, FadeIn } from '@/components/Motion';
import { MyUserContext } from '@/config/Contexts';
import { fonts, useThemeColors, useThemeStyles } from '@/constants/theme';

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
      <StatusBar style={colors.statusBar} />
      <AmbientGlow height={420} />
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
        <FadeIn style={styles.identity} distance={18}>
          <Breathing style={styles.avatarRing} duration={3600} scaleTo={1.04}>
            <View style={styles.avatar}><Text style={styles.avatarText}>{getInitials(user?.full_name || '')}</Text></View>
          </Breathing>
          <Text style={styles.name}>{user?.full_name || 'Người dùng'}</Text>
          <View style={styles.planBadge}><Text style={styles.plan}>Free</Text></View>
        </FadeIn>
        <FadeIn style={styles.card} delay={140} distance={18}>
          {details.map(({ label, value }, index) => (
            <View key={label} style={[styles.detailRow, index > 0 && styles.divided]}>
              <Text style={styles.label}>{label}</Text>
              <Text style={styles.value}>{value}</Text>
            </View>
          ))}
          {details.length === 0 ? <Text style={styles.empty}>Chưa có thông tin hồ sơ.</Text> : null}
        </FadeIn>
        <FadeIn style={styles.note} delay={260}>
          <ProfileIcon size={16} color={colors.gold} />
          <Text style={styles.noteText}>Thông tin hồ sơ của tài khoản đang đăng nhập.</Text>
        </FadeIn>
      </View>
    </View>
  );
}

const createStyles = (colors) => StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  header: {
    minHeight: 60,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
  },
  backButton: {
    width: 42,
    height: 42,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 21,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
  },
  title: { color: colors.text, fontFamily: fonts.display, fontSize: 19, fontWeight: '600' },
  headerSpacer: { width: 42 },
  content: { width: '100%', maxWidth: 560, alignSelf: 'center', padding: 20 },
  identity: { alignItems: 'center', paddingTop: 20, paddingBottom: 28 },
  avatarRing: {
    padding: 5,
    borderRadius: 54,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
    shadowColor: colors.glow,
    shadowOpacity: 0.3,
    shadowRadius: 22,
    shadowOffset: { width: 0, height: 8 },
    elevation: 5,
  },
  avatar: {
    width: 92,
    height: 92,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 46,
    borderWidth: 1,
    borderColor: colors.gold,
    backgroundColor: colors.avatar,
  },
  avatarText: { color: colors.onAvatar, fontFamily: fonts.display, fontSize: 32, fontWeight: '600', letterSpacing: 1 },
  name: { color: colors.text, fontFamily: fonts.display, fontSize: 25, fontWeight: '600', marginTop: 18 },
  planBadge: {
    marginTop: 10,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
  },
  plan: { color: colors.gold, fontSize: 11, fontWeight: '700', letterSpacing: 1.6, textTransform: 'uppercase' },
  card: {
    paddingHorizontal: 18,
    borderRadius: 22,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.card,
  },
  detailRow: { minHeight: 64, justifyContent: 'center', gap: 5, paddingVertical: 10 },
  divided: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.borderStrong },
  label: { color: colors.textMuted, fontSize: 11, fontWeight: '700', letterSpacing: 1.2, textTransform: 'uppercase' },
  value: { color: colors.text, fontSize: 16, fontWeight: '500' },
  empty: { color: colors.textSecondary, fontSize: 14, paddingVertical: 18 },
  note: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 16, paddingHorizontal: 6 },
  noteText: { flex: 1, color: colors.textMuted, fontSize: 13 },
  pressed: { opacity: 0.7 },
});
