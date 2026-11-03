import { router } from 'expo-router';
import { use, useRef, useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import AuthButton from '@/components/AuthButton';
import AuthField from '@/components/AuthField';
import { LockIcon, PhoneIcon } from '@/components/AuthIcons';
import AuthScreen from '@/components/AuthScreen';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import { getErrorMessage, isValidPhone, login } from '@/services/auth';

export default function Login() {
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

      {formError ? <Text style={styles.formError}>{formError}</Text> : null}
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

const styles = StyleSheet.create({
  formError: {
    color: colors.error,
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 12,
  },
  forgot: {
    alignSelf: 'center',
    marginTop: 16,
  },
  forgotText: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '600',
  },
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginVertical: 16,
  },
  dividerLine: {
    flex: 1,
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.divider,
  },
  dividerText: {
    color: colors.textMuted,
    fontSize: 13,
  },
  footerText: {
    color: colors.textMuted,
    fontSize: 13,
  },
  footerLink: {
    color: colors.text,
    fontWeight: '600',
  },
});
