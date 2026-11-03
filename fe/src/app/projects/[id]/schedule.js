import { router, useLocalSearchParams } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use, useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import AuthButton from '@/components/AuthButton';
import AuthField from '@/components/AuthField';
import { CalendarIcon, ClockIcon, EditIcon } from '@/components/HomeIcons';
import PageHeader from '@/components/PageHeader';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import { getErrorMessage } from '@/services/auth';
import { createSchedule, validateScheduleTime } from '@/services/schedules';

const MAX_NAME_LENGTH = 255;
const MAX_CONTENT_LENGTH = 20000;

export default function NewSchedule() {
  const { id } = useLocalSearchParams();
  const [user] = use(MyUserContext);
  const [name, setName] = useState('');
  const [time, setTime] = useState('');
  const [content, setContent] = useState('');
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const timeRef = useRef(null);
  const contentRef = useRef(null);

  const handleSave = async () => {
    const trimmedTime = time.trim();
    const nextErrors = {};
    if (!name.trim()) nextErrors.name = 'Vui lòng nhập tên lịch';
    const timeError = validateScheduleTime(trimmedTime);
    if (timeError) nextErrors.time = timeError;
    if (!content.trim()) nextErrors.content = 'Vui lòng nhập nội dung';
    setErrors(nextErrors);
    setFormError('');
    if (Object.keys(nextErrors).length > 0) return;

    setSaving(true);
    try {
      await createSchedule(user.access_token, {
        projectId: id,
        name: name.trim(),
        time: trimmedTime,
        content: content.trim(),
      });
      router.back();
    } catch (error) {
      setFormError(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />
      <PageHeader title="Đặt lịch" />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.page}>
            <AuthField
              label="Tên lịch"
              icon={<CalendarIcon size={20} color={colors.textMuted} />}
              error={errors.name}
              value={name}
              onChangeText={setName}
              placeholder="Nhập tên lịch"
              maxLength={MAX_NAME_LENGTH}
              returnKeyType="next"
              onSubmitEditing={() => timeRef.current?.focus()}
            />
            <AuthField
              ref={timeRef}
              label="Thời gian"
              icon={<ClockIcon size={20} color={colors.textMuted} />}
              error={errors.time}
              value={time}
              onChangeText={setTime}
              placeholder="05/11/2026 20:00"
              keyboardType="numbers-and-punctuation"
              autoCorrect={false}
              returnKeyType="next"
              onSubmitEditing={() => contentRef.current?.focus()}
            />
            <AuthField
              ref={contentRef}
              label="Nội dung"
              icon={<EditIcon size={20} color={colors.textMuted} />}
              error={errors.content}
              value={content}
              onChangeText={setContent}
              placeholder="Agent sẽ nhận nội dung này khi đến giờ"
              maxLength={MAX_CONTENT_LENGTH}
              returnKeyType="done"
              onSubmitEditing={handleSave}
            />

            {formError ? <Text style={styles.formError}>{formError}</Text> : null}
            <AuthButton title="Lưu lịch" onPress={handleSave} loading={saving} />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.backgroundDeep,
  },
  flex: {
    flex: 1,
  },
  content: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 40,
  },
  page: {
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
  },
  formError: {
    color: colors.error,
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 12,
  },
});
