import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use, useCallback, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import AuthButton from '@/components/AuthButton';
import { MessageAttachments } from '@/components/ChatAttachments';
import { CheckIcon } from '@/components/HomeIcons';
import MonthCalendar from '@/components/MonthCalendar';
import PageHeader from '@/components/PageHeader';
import TimePickerSheet from '@/components/TimePickerSheet';
import { MyUserContext } from '@/config/Contexts';
import { useThemeColors, useThemeStyles } from '@/constants/theme';
import { getErrorMessage } from '@/services/auth';
import { createSchedule, getScheduleNow, getSchedules, PLATFORMS, validateScheduleTime } from '@/services/schedules';
import { getMessages } from '@/services/projects';

const NO_MARKS = new Set();
const TIMEZONE = 'Asia/Ho_Chi_Minh';
const MAX_MESSAGE_PAGES = 20;
const pad = (value) => String(value).padStart(2, '0');

const getConversationMessages = async (token, conversationId) => {
  const messages = [];
  let before;
  for (let pageNumber = 0; pageNumber < MAX_MESSAGE_PAGES; pageNumber += 1) {
    const page = await getMessages(token, conversationId, before);
    messages.push(...page.items);
    if (!page.next_before) break;
    before = page.next_before;
  }
  return messages;
};

const getMessageLabel = (message) => {
  const text = message.content?.trim();
  if (text) return text;
  const attachments = message.attachments ?? [];
  return attachments.length ? `Nội dung có ${attachments.length} tệp đính kèm` : 'Nội dung không có văn bản';
};

export default function NewSchedule() {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

  const { id, contentMessageId } = useLocalSearchParams();
  const [user] = use(MyUserContext);
  const [now] = useState(getScheduleNow);
  const [view, setView] = useState({ year: now.year, month: now.month });
  const [platforms, setPlatforms] = useState([]);
  const [availableMessages, setAvailableMessages] = useState(null);
  const [selectedContentId, setSelectedContentId] = useState(null);
  const [contentError, setContentError] = useState('');
  const [contentLoadError, setContentLoadError] = useState('');
  const [selectedKey, setSelectedKey] = useState(null);
  const [hour, setHour] = useState((now.hour + 1) % 24);
  const [minute, setMinute] = useState(0);
  const [pickingTime, setPickingTime] = useState(false);
  const [platformError, setPlatformError] = useState('');
  const [timeError, setTimeError] = useState('');
  const [saving, setSaving] = useState(false);
  const saved = useRef(false);

  useFocusEffect(
    useCallback(() => {
      if (!user?.access_token || !id) return undefined;
      let active = true;
      setAvailableMessages(null);
      Promise.all([
        getConversationMessages(user.access_token, id),
        getSchedules(user.access_token),
      ])
        .then(([messages, schedules]) => {
          if (!active) return;
          const selected = messages.find((message) => String(message.id) === String(contentMessageId));
          const alreadyScheduled = schedules.some((schedule) =>
            String(schedule.conversation_id) === String(id)
            && String(schedule.content_message_id) === String(contentMessageId)
          );
          const available = selected
            && selected.role === 'assistant'
            && selected.status === 'completed'
            && (selected.content?.trim() || selected.attachments?.length > 0)
            && !alreadyScheduled
            ? [selected]
            : [];
          setAvailableMessages(available);
          setSelectedContentId(available[0]?.id ?? null);
          setContentLoadError(available.length ? '' : alreadyScheduled
            ? 'Tin nhắn này đã được lên lịch rồi.'
            : 'Không tìm thấy tin nhắn assistant hợp lệ để lên lịch.');
        })
        .catch((error) => {
          if (active) {
            setAvailableMessages([]);
            setContentLoadError(getErrorMessage(error));
          }
        });
      return () => { active = false; };
    }, [contentMessageId, id, user?.access_token])
  );

  const selectedContent = useMemo(
    () => availableMessages?.find((message) => String(message.id) === String(selectedContentId)) ?? null,
    [availableMessages, selectedContentId]
  );

  const togglePlatform = (platform) => {
    setPlatformError('');
    setPlatforms((current) =>
      current.includes(platform) ? current.filter((item) => item !== platform) : [...current, platform]
    );
  };

  const changeMonth = (delta) => {
    setView(({ year, month }) => {
      const next = new Date(year, month + delta, 1);
      return { year: next.getFullYear(), month: next.getMonth() };
    });
  };

  const openTimePicker = () => {
    if (!selectedContent) {
      setContentError('Vui lòng chọn nội dung assistant đã tạo trước khi đặt lịch.');
      return;
    }
    if (platforms.length === 0) {
      setPlatformError('Vui lòng chọn ít nhất một nền tảng');
      return;
    }
    setTimeError('');
    setPickingTime(true);
  };

  const selectDay = (key) => {
    setSelectedKey(key);
    openTimePicker();
  };

  const handleSheetClosed = useCallback(() => {
    if (saved.current) router.back();
  }, []);

  const selectedDate = selectedKey ? selectedKey.split('-').reverse().join('/') : '';

  const handleSave = async () => {
    if (!selectedContent) {
      setContentError('Vui lòng chọn nội dung cần gắn lịch.');
      setPickingTime(false);
      return;
    }
    const time = `${selectedDate} ${pad(hour)}:${pad(minute)}`;
    const invalid = validateScheduleTime(time);
    setTimeError(invalid ?? '');
    if (invalid) return;

    setSaving(true);
    try {
      await createSchedule(user.access_token, {
        projectId: id,
        contentMessageId: selectedContent.id,
        platforms,
        scheduledAt: `${selectedKey}T${pad(hour)}:${pad(minute)}:00+07:00`,
        timezone: TIMEZONE,
      });
      saved.current = true;
      setPickingTime(false);
    } catch (error) {
      setTimeError(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style={colors.backgroundDeep === '#000000' ? 'light' : 'dark'} />
      <PageHeader title="Đặt lịch" />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.page}>
          <Text style={styles.sectionTitle}>Nội dung đã chọn</Text>
          <View style={styles.contentPreview}>
            {availableMessages === null ? (
              <ActivityIndicator color={colors.text} />
            ) : selectedContent ? (
              <Text style={styles.contentPreviewText}>{getMessageLabel(selectedContent)}</Text>
            ) : (
              <Text style={styles.contentPreviewText}>Không tìm thấy nội dung đã chọn</Text>
            )}
          </View>
          {contentLoadError ? <Text style={styles.error}>{contentLoadError}</Text> : null}
          {contentError ? <Text style={styles.error}>{contentError}</Text> : null}
          {selectedContent?.attachments?.length ? (
            <View style={styles.selectedAttachments}>
              <MessageAttachments attachments={selectedContent.attachments} />
            </View>
          ) : null}

          <Text style={styles.sectionTitle}>Nền tảng muốn đăng</Text>
          <View style={styles.platforms}>
            {PLATFORMS.map((platform) => {
              const checked = platforms.includes(platform);
              return (
                <Pressable
                  key={platform}
                  onPress={() => togglePlatform(platform)}
                  style={({ pressed }) => [styles.platform, checked && styles.platformChecked, pressed && styles.pressed]}
                  accessibilityRole="checkbox"
                  accessibilityLabel={platform}
                  accessibilityState={{ checked }}
                >
                  {checked ? <CheckIcon size={16} color={colors.onPrimary} /> : null}
                  <Text style={[styles.platformLabel, checked && styles.platformLabelChecked]}>{platform}</Text>
                </Pressable>
              );
            })}
          </View>
          {platformError ? <Text style={styles.error}>{platformError}</Text> : null}

          <Text style={[styles.sectionTitle, styles.dateTitle]}>Ngày đăng</Text>
          <MonthCalendar
            year={view.year}
            month={view.month}
            selectedKey={selectedKey}
            minKey={now.dayKey}
            markedKeys={NO_MARKS}
            onSelectDay={selectDay}
            onChangeMonth={changeMonth}
          />

          {selectedKey ? (
            <View style={styles.timeButton}>
              <AuthButton title="Chọn giờ" onPress={openTimePicker} />
            </View>
          ) : null}
        </View>
      </ScrollView>

      <TimePickerSheet
        visible={pickingTime}
        title={`Giờ đăng ngày ${selectedDate}`}
        hour={hour}
        minute={minute}
        error={timeError}
        saving={saving}
        onChangeHour={setHour}
        onChangeMinute={setMinute}
        onSave={handleSave}
        onClose={() => setPickingTime(false)}
        onClosed={handleSheetClosed}
      />
    </SafeAreaView>
  );
}

const createStyles = (colors) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.backgroundDeep,
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
  sectionTitle: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: '600',
    marginBottom: 12,
  },
  contentPreview: {
    minHeight: 52,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 14,
    borderRadius: 14,
    backgroundColor: colors.surface,
  },
  contentPreviewText: {
    color: colors.text,
    fontSize: 15,
    lineHeight: 21,
    alignSelf: 'stretch',
  },
  selectedAttachments: {
    marginTop: 10,
  },
  dateTitle: {
    marginTop: 24,
    marginBottom: 4,
  },
  platforms: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  platform: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 16,
    borderRadius: 22,
    backgroundColor: colors.surface,
  },
  platformChecked: {
    backgroundColor: colors.primary,
  },
  pressed: {
    opacity: 0.7,
  },
  platformLabel: {
    color: colors.text,
    fontSize: 15,
  },
  platformLabelChecked: {
    color: colors.onPrimary,
    fontWeight: '600',
  },
  error: {
    color: colors.error,
    fontSize: 14,
    marginTop: 12,
  },
  timeButton: {
    marginTop: 16,
  },
});
