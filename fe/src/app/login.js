import { router } from 'expo-router';
import { use, useRef, useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import AuthButton from '@/components/AuthButton';
import AuthField from '@/components/AuthField';
import { LockIcon, PhoneIcon } from '@/components/AuthIcons';
import AuthScreen from '@/components/AuthScreen';
import { FadeIn } from '@/components/Motion';
import { MyUserContext } from '@/config/Contexts';
import { useThemeStyles } from '@/constants/theme';
import { getErrorMessage, isValidPhone, login } from '@/services/auth';

export default function Login() {
  const styles = useThemeStyles(createStyles);

  const [, dispatch] = use(MyUserContext);
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [loading, setLoading] = useState(false);
  const passwordRef = useRef(null);

  const handleLogin = async () => {
    const nextErrors = {};
    if (!isValidPhone(phone)) nextErrors.phone = 'Số điện thoại không hợp lệ';
    if (!password) nextErrors.password = 'Vui lòng nhập mật khẩu';
    setErrors(nextErrors);
    setFormError('');
    if (Object.keys(nextErrors).length > 0) return;

    setLoading(true);
    try {
      dispatch({ type: 'LOGIN', payload: await login(phone, password) });
    } catch (error) {
      setFormError(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  // Backend chưa có API đặt lại mật khẩu cho tài khoản số điện thoại
  const handleForgotPassword = () => {
    Alert.alert('Quên mật khẩu', 'Liên hệ nhu.digitalmkt để được cấp lại mật khẩu.');
  };

  return (
    <AuthScreen
      title="nhu video AI"
      subtitle="Quay bằng điện thoại – AI dựng & đăng giúp bạn"
      footer={
        <Pressable accessibilityRole="link" onPress={() => router.push('/register')} hitSlop={8}>
          <Text style={styles.footerText}>
            Chưa có tài khoản? <Text style={styles.footerLink}>Đăng ký</Text>
          </Text>
        </Pressable>
      }
    >
      <AuthField
        label="Số điện thoại"
        icon={<PhoneIcon />}
        error={errors.phone}
        value={phone}
        onChangeText={setPhone}
        placeholder="0912 345 678"
        keyboardType="phone-pad"
        autoComplete="tel"
        textContentType="telephoneNumber"
        returnKeyType="next"
        onSubmitEditing={() => passwordRef.current?.focus()}
      />
      <AuthField
        ref={passwordRef}
        label="Mật khẩu"
        icon={<LockIcon />}
        error={errors.password}
        value={password}
        onChangeText={setPassword}
        placeholder="••••••••"
        secureTextEntry
        autoCapitalize="none"
        autoComplete="current-password"
        textContentType="password"
        returnKeyType="done"
        onSubmitEditing={handleLogin}
      />

      {formError ? <FadeIn key={formError} distance={-6} duration={320}><Text style={styles.formError}>{formError}</Text></FadeIn> : null}
      <AuthButton title="Đăng nhập" onPress={handleLogin} loading={loading} />

      <Pressable
        accessibilityRole="button"
        onPress={handleForgotPassword}
        style={styles.forgot}
        hitSlop={8}
      >
        <Text style={styles.forgotText}>Quên mật khẩu?</Text>
      </Pressable>

      <View style={styles.dividerRow}>
        <View style={styles.dividerLine} />
        <Text style={styles.dividerText}>hoặc</Text>
        <View style={styles.dividerLine} />
      </View>

      <AuthButton
        title="Tiếp tục với số điện thoại"
        variant="secondary"
        onPress={() => router.push('/register')}
      />
    </AuthScreen>
  );
}

const createStyles = (colors) => StyleSheet.create({
  formError: {
    color: colors.error,
    fontSize: 13.5,
    lineHeight: 19,
    textAlign: 'center',
    marginBottom: 14,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.errorBorder,
    backgroundColor: colors.errorSoft,
    overflow: 'hidden',
  },
  forgot: {
    alignSelf: 'center',
    marginTop: 16,
  },
  forgotText: {
    color: colors.gold,
    fontSize: 13.5,
    fontWeight: '600',
    letterSpacing: 0.2,
  },
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginVertical: 18,
  },
  dividerLine: {
    flex: 1,
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.borderStrong,
  },
  dividerText: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 1.6,
    textTransform: 'uppercase',
  },
  footerText: {
    color: colors.textSecondary,
    fontSize: 14,
  },
  footerLink: {
    color: colors.gold,
    fontWeight: '700',
  },
});
