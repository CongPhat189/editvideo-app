import { router } from 'expo-router';
import { use, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text } from 'react-native';

import AuthButton from '@/components/AuthButton';
import AuthField from '@/components/AuthField';
import { LockIcon, PhoneIcon, UserIcon } from '@/components/AuthIcons';
import AuthScreen from '@/components/AuthScreen';
import { FadeIn } from '@/components/Motion';
import { MyUserContext } from '@/config/Contexts';
import { useThemeStyles } from '@/constants/theme';
import { getErrorMessage, isValidPhone, MIN_PASSWORD_LENGTH, register } from '@/services/auth';

export default function Register() {
  const styles = useThemeStyles(createStyles);

  const [, dispatch] = use(MyUserContext);
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [loading, setLoading] = useState(false);
  const phoneRef = useRef(null);
  const passwordRef = useRef(null);
  const confirmPasswordRef = useRef(null);

  const handleRegister = async () => {
    const nextErrors = {};
    if (!fullName.trim()) nextErrors.fullName = 'Vui lòng nhập họ và tên';
    if (!isValidPhone(phone)) nextErrors.phone = 'Số điện thoại không hợp lệ';
    if (password.length < MIN_PASSWORD_LENGTH) {
      nextErrors.password = `Mật khẩu cần ít nhất ${MIN_PASSWORD_LENGTH} ký tự`;
    }
    if (confirmPassword !== password) nextErrors.confirmPassword = 'Mật khẩu nhập lại không khớp';
    setErrors(nextErrors);
    setFormError('');
    if (Object.keys(nextErrors).length > 0) return;

    setLoading(true);
    try {
      dispatch({ type: 'LOGIN', payload: await register(fullName, phone, password) });
    } catch (error) {
      setFormError(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  const goToLogin = () => {
    if (router.canGoBack()) router.back();
    else router.replace('/login');
  };

  return (
    <AuthScreen
      title="Tạo tài khoản"
      subtitle="Đăng ký bằng số điện thoại để bắt đầu"
      footer={
        <Pressable accessibilityRole="link" onPress={goToLogin} hitSlop={8}>
          <Text style={styles.footerText}>
            Đã có tài khoản? <Text style={styles.footerLink}>Đăng nhập</Text>
          </Text>
        </Pressable>
      }
    >
      <AuthField
        label="Họ và tên"
        icon={<UserIcon />}
        error={errors.fullName}
        value={fullName}
        onChangeText={setFullName}
        placeholder="Nguyễn Văn A"
        autoCapitalize="words"
        autoComplete="name"
        textContentType="name"
        returnKeyType="next"
        onSubmitEditing={() => phoneRef.current?.focus()}
      />
      <AuthField
        ref={phoneRef}
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
        placeholder="Ít nhất 8 ký tự"
        secureTextEntry
        autoCapitalize="none"
        autoComplete="new-password"
        textContentType="newPassword"
        returnKeyType="next"
        onSubmitEditing={() => confirmPasswordRef.current?.focus()}
      />
      <AuthField
        ref={confirmPasswordRef}
        label="Nhập lại mật khẩu"
        icon={<LockIcon />}
        error={errors.confirmPassword}
        value={confirmPassword}
        onChangeText={setConfirmPassword}
        placeholder="••••••••"
        secureTextEntry
        autoCapitalize="none"
        autoComplete="new-password"
        textContentType="newPassword"
        returnKeyType="done"
        onSubmitEditing={handleRegister}
      />

      {formError ? <FadeIn key={formError} distance={-6} duration={320}><Text style={styles.formError}>{formError}</Text></FadeIn> : null}
      <AuthButton title="Đăng ký" onPress={handleRegister} loading={loading} />
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
  footerText: {
    color: colors.textSecondary,
    fontSize: 14,
  },
  footerLink: {
    color: colors.gold,
    fontWeight: '700',
  },
});
