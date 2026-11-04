import { router, useLocalSearchParams } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use, useCallback, useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import AuthButton from '@/components/AuthButton';
import { CheckIcon } from '@/components/HomeIcons';
import MonthCalendar from '@/components/MonthCalendar';
import PageHeader from '@/components/PageHeader';
import TimePickerSheet from '@/components/TimePickerSheet';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import { getErrorMessage } from '@/services/auth';
import { createSchedule, getScheduleNow, PLATFORMS, validateScheduleTime } from '@/services/schedules';

const NO_MARKS = new Set();
const pad = (value) => String(value).padStart(2, '0');

export default function NewSchedule() {
  const { id } = useLocalSearchParams();
  const [user] = use(MyUserContext);
  const [now] = useState(getScheduleNow);
  const [view, setView] = useState({ year: now.year, month: now.month });
  const [platforms, setPlatforms] = useState([]);
  const [selectedKey, setSelectedKey] = useState(null);
  const [hour, setHour] = useState((now.hour + 1) % 24);
  const [minute, setMinute] = useState(0);
  const [pickingTime, setPickingTime] = useState(false);
  const [platformError, setPlatformError] = useState('');
  const [timeError, setTimeError] = useState('');
  const [saving, setSaving] = useState(false);
  const saved = useRef(false);

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
    const time = `${selectedDate} ${pad(hour)}:${pad(minute)}`;
    const invalid = validateScheduleTime(time);
    setTimeError(invalid ?? '');
    if (invalid) return;

    setSaving(true);
    try {
      await createSchedule(user.access_token, { projectId: id, platforms, time });
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
      <StatusBar style="light" />
      <PageHeader title="Đặt lịch" />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.page}>
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

const styles = StyleSheet.create({
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
