import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use, useCallback, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import AuthButton from '@/components/AuthButton';
import { CheckIcon } from '@/components/HomeIcons';
import MonthCalendar from '@/components/MonthCalendar';
import { Eyebrow } from '@/components/Luxe';
import { FadeIn, PopIn, stagger } from '@/components/Motion';
import PageHeader from '@/components/PageHeader';
import PlatformIcon from '@/components/PlatformIcons';
import TimePickerSheet from '@/components/TimePickerSheet';
import { MyUserContext } from '@/config/Contexts';
import { fonts, useThemeColors, useThemeStyles } from '@/constants/theme';
import { getErrorMessage } from '@/services/auth';
import { createSchedule, getScheduleNow, isScheduleContent, PLATFORMS, validateScheduleTime } from '@/services/schedules';
import { getMessages } from '@/services/projects';

const NO_MARKS = new Set();
const TIMEZONE = 'Asia/Ho_Chi_Minh';
const pad = (value) => String(value).padStart(2, '0');

export default function NewSchedule() {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

  const { id } = useLocalSearchParams();
  const [user] = use(MyUserContext);
  const [now] = useState(getScheduleNow);
  const [view, setView] = useState({ year: now.year, month: now.month });
  const [platforms, setPlatforms] = useState([]);
  // undefined: đang tải, null: chưa có content
  const [content, setContent] = useState(undefined);
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
      setContent(undefined);
      // Tin mới nhất trước: lấy tin agent trả lời gần nhất làm content
      getMessages(user.access_token, id)
        .then((page) => {
          if (!active) return;
          const latest = page.items.find(isScheduleContent);
          setContent(latest ? latest.content.trim() : null);
          setContentLoadError(latest ? '' : 'Chưa có content nào. Hãy nhờ Agent tạo content trước.');
        })
        .catch((error) => {
          if (active) {
            setContent(null);
            setContentLoadError(getErrorMessage(error));
          }
        });
      return () => { active = false; };
    }, [id, user?.access_token])
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
    if (!content) {
      setContentError('Chưa có content để đặt lịch.');
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
    if (!content) {
      setContentError('Chưa có content để đặt lịch.');
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
        content,
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
          <Text style={styles.sectionTitle}>Content sẽ đăng</Text>
          <FadeIn style={styles.contentPreview} delay={100}>
            {content === undefined ? (
              <ActivityIndicator color={colors.gold} />
            ) : content ? (
              <Text style={styles.contentPreviewText}>{content}</Text>
            ) : (
              <Text style={styles.contentPreviewText}>Không có content</Text>
            )}
          </FadeIn>
          {contentLoadError ? <Text style={styles.error}>{contentLoadError}</Text> : null}
          {contentError ? <Text style={styles.error}>{contentError}</Text> : null}

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
                  <PlatformIcon platform={platform} size={22} />
                  <Text style={[styles.platformLabel, checked && styles.platformLabelChecked]}>{platform}</Text>
                  {checked ? <PopIn><CheckIcon size={15} color={colors.onPrimary} /></PopIn> : null}
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
    gap: 8,
    paddingLeft: 12,
    paddingRight: 16,
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
