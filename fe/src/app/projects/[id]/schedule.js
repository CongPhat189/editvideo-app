import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use, useCallback, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import AuthButton from '@/components/AuthButton';
import { MessageAttachments } from '@/components/ChatAttachments';
import { CheckIcon } from '@/components/HomeIcons';
import MonthCalendar from '@/components/MonthCalendar';
import { Eyebrow } from '@/components/Luxe';
import { FadeIn, PopIn, stagger } from '@/components/Motion';
import PageHeader from '@/components/PageHeader';
import TimePickerSheet from '@/components/TimePickerSheet';
import { MyUserContext } from '@/config/Contexts';
import { fonts, useThemeColors, useThemeStyles } from '@/constants/theme';
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
      <StatusBar style={colors.statusBar} />
      <PageHeader title="Đặt lịch" />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.page}>
          <FadeIn style={styles.intro}>
            <Eyebrow>Lên lịch đăng</Eyebrow>
            <Text style={styles.introTitle}>Chọn nền tảng và thời gian</Text>
          </FadeIn>
          <Text style={styles.sectionTitle}>Nội dung đã chọn</Text>
          <FadeIn style={styles.contentPreview} delay={100}>
            {availableMessages === null ? (
              <ActivityIndicator color={colors.gold} />
            ) : selectedContent ? (
              <Text style={styles.contentPreviewText}>{getMessageLabel(selectedContent)}</Text>
            ) : (
              <Text style={styles.contentPreviewText}>Không tìm thấy nội dung đã chọn</Text>
            )}
          </FadeIn>
          {contentLoadError ? <Text style={styles.error}>{contentLoadError}</Text> : null}
          {contentError ? <Text style={styles.error}>{contentError}</Text> : null}
          {selectedContent?.attachments?.length ? (
            <View style={styles.selectedAttachments}>
              <MessageAttachments attachments={selectedContent.attachments} />
            </View>
          ) : null}

          <Text style={styles.sectionTitle}>Nền tảng muốn đăng</Text>
          <View style={styles.platforms}>
            {PLATFORMS.map((platform, index) => {
              const checked = platforms.includes(platform);
              return (
                <FadeIn key={platform} delay={stagger(index, 50, 180)} distance={10}>
                <Pressable
                  onPress={() => togglePlatform(platform)}
                  style={({ pressed }) => [styles.platform, checked && styles.platformChecked, pressed && styles.pressed]}
                  accessibilityRole="checkbox"
                  accessibilityLabel={platform}
                  accessibilityState={{ checked }}
                >
                  {checked ? <PopIn><CheckIcon size={16} color={colors.onPrimary} /></PopIn> : null}
                  <Text style={[styles.platformLabel, checked && styles.platformLabelChecked]}>{platform}</Text>
                </Pressable>
                </FadeIn>
              );
            })}
          </View>
          {platformError ? <Text style={styles.error}>{platformError}</Text> : null}

          <Text style={[styles.sectionTitle, styles.dateTitle]}>Ngày đăng</Text>
          <FadeIn delay={320} distance={18}>
          <MonthCalendar
            year={view.year}
            month={view.month}
            selectedKey={selectedKey}
            minKey={now.dayKey}
            markedKeys={NO_MARKS}
            onSelectDay={selectDay}
            onChangeMonth={changeMonth}
          />
          </FadeIn>

          {selectedKey ? (
            <FadeIn style={styles.timeButton} distance={10}>
              <AuthButton title="Chọn giờ" onPress={openTimePicker} />
            </FadeIn>
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
    backgroundColor: colors.background,
  },
  content: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 40,
  },
  page: {
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
  },
  intro: {
    marginBottom: 0,
  },
  introTitle: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 24,
    lineHeight: 31,
    fontWeight: '600',
    marginTop: 8,
  },
  sectionTitle: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 0.4,
    marginTop: 24,
    marginBottom: 10,
    marginLeft: 2,
  },
  contentPreview: {
    minHeight: 56,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderLeftWidth: 3,
    borderColor: colors.borderStrong,
    borderLeftColor: colors.gold,
    backgroundColor: colors.card,
  },
  contentPreviewText: {
    color: colors.text,
    fontSize: 15,
    lineHeight: 22,
    alignSelf: 'stretch',
  },
  selectedAttachments: {
    marginTop: 10,
  },
  dateTitle: {
    marginTop: 28,
    marginBottom: 10,
  },
  platforms: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  platform: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 18,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: colors.card,
  },
  platformChecked: {
    borderColor: colors.gold,
    backgroundColor: colors.primary,
  },
  pressed: {
    opacity: 0.75,
  },
  platformLabel: {
    color: colors.text,
    fontSize: 14.5,
    fontWeight: '500',
  },
  platformLabelChecked: {
    color: colors.onPrimary,
    fontWeight: '700',
  },
  error: {
    color: colors.error,
    fontSize: 13.5,
    lineHeight: 19,
    marginTop: 10,
  },
  timeButton: {
    marginTop: 20,
  },
});
