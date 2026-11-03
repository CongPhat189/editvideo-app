import { router, useFocusEffect } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use, useCallback, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ChevronRightIcon } from '@/components/HomeIcons';
import MonthCalendar, { toDayKey } from '@/components/MonthCalendar';
import PageHeader from '@/components/PageHeader';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import { getErrorMessage } from '@/services/auth';
import { getProjects } from '@/services/projects';
import { formatScheduleTime, getScheduleDayKey, getSchedules } from '@/services/schedules';

const DetailRow = ({ label, value }) => (
  <View style={styles.detailRow}>
    <Text style={styles.detailLabel}>{label}</Text>
    <Text style={styles.detailValue} selectable>{value}</Text>
  </View>
);

export default function Scheduled() {
  const [user] = use(MyUserContext);
  const token = user?.access_token;
  const [view, setView] = useState(() => {
    const today = new Date();
    return { year: today.getFullYear(), month: today.getMonth() };
  });
  const [selectedKey, setSelectedKey] = useState(() => toDayKey(new Date()));
  const [schedules, setSchedules] = useState(null);
  const [projectNames, setProjectNames] = useState({});
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState('');

  useFocusEffect(
    useCallback(() => {
      if (!token) return undefined;
      let active = true;
      Promise.all([getSchedules(token), getProjects(token)])
        .then(([scheduleItems, projects]) => {
          if (!active) return;
          setSchedules(scheduleItems);
          setProjectNames(Object.fromEntries(projects.map((project) => [project.id, project.title])));
          setError('');
        })
        .catch((err) => {
          if (!active) return;
          setSchedules([]);
          setError(getErrorMessage(err));
        });
      return () => {
        active = false;
      };
    }, [token])
  );

  const markedKeys = useMemo(() => new Set((schedules ?? []).map(getScheduleDayKey)), [schedules]);
  const daySchedules = useMemo(
    () =>
      (schedules ?? [])
        .filter((schedule) => getScheduleDayKey(schedule) === selectedKey)
        .sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at)),
    [schedules, selectedKey]
  );
  const selected = daySchedules.find((schedule) => schedule.id === selectedId);

  const changeMonth = (delta) => {
    setView(({ year, month }) => {
      const next = new Date(year, month + delta, 1);
      return { year: next.getFullYear(), month: next.getMonth() };
    });
  };

  const selectDay = (key) => {
    setSelectedKey(key);
    setSelectedId(null);
  };

  const projectName = selected ? projectNames[selected.conversation_id] : null;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />
      <PageHeader title="Đã lên lịch" />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.page}>
          <MonthCalendar
            year={view.year}
            month={view.month}
            selectedKey={selectedKey}
            markedKeys={markedKeys}
            onSelectDay={selectDay}
            onChangeMonth={changeMonth}
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}
          {schedules === null ? <ActivityIndicator color={colors.text} style={styles.loading} /> : null}

          {schedules?.length === 0 && !error ? (
            <View style={styles.empty}>
              <Text style={styles.emptyTitle}>Chưa có lịch nào</Text>
              <Text style={styles.emptyBody}>Mở một dự án và đặt lịch ngay trong Chat, lịch sẽ hiện ở đây.</Text>
            </View>
          ) : null}

          {schedules?.length > 0 && daySchedules.length === 0 ? (
            <Text style={styles.noSchedule}>Không có lịch trong ngày này</Text>
          ) : null}

          {daySchedules.length > 0 ? (
            <View style={styles.card}>
              {daySchedules.map((schedule, index) => (
                <Pressable
                  key={schedule.id}
                  onPress={() => setSelectedId(schedule.id)}
                  style={({ pressed }) => [styles.row, pressed && styles.pressed]}
                  accessibilityRole="button"
                  accessibilityLabel={schedule.task_name}
                  aria-selected={schedule.id === selectedId}
                >
                  <View style={[styles.rowBody, index > 0 && styles.rowDivider]}>
                    <Text style={styles.rowTime}>{formatScheduleTime(schedule).slice(11)}</Text>
                    <Text style={styles.rowLabel} numberOfLines={1}>{schedule.task_name}</Text>
                    <ChevronRightIcon size={20} color={colors.textSecondary} />
                  </View>
                </Pressable>
              ))}
            </View>
          ) : null}

          {selected ? (
            <View style={styles.detail}>
              <DetailRow label="Tên" value={selected.task_name} />
              <DetailRow label="Thời gian" value={formatScheduleTime(selected)} />
              <DetailRow label="Nội dung" value={selected.content || 'Không có nội dung'} />
              <Pressable
                onPress={() => router.push(`/projects/${selected.conversation_id}`)}
                disabled={!projectName}
                style={({ pressed }) => [styles.projectRow, pressed && styles.pressed]}
                accessibilityRole="button"
                accessibilityLabel={`Mở dự án ${projectName ?? ''}`}
              >
                <View style={styles.projectText}>
                  <Text style={styles.detailLabel}>Dự án</Text>
                  <Text style={styles.detailValue} numberOfLines={1}>
                    {projectName || 'Không tìm thấy dự án'}
                  </Text>
                </View>
                {projectName ? <ChevronRightIcon size={20} color={colors.textSecondary} /> : null}
              </Pressable>
            </View>
          ) : null}
        </View>
      </ScrollView>
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
    paddingTop: 8,
    paddingBottom: 40,
  },
  page: {
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
  },
  loading: {
    marginTop: 32,
  },
  error: {
    color: colors.error,
    fontSize: 14,
    textAlign: 'center',
    marginTop: 24,
  },
  empty: {
    alignItems: 'center',
    marginTop: 32,
    paddingHorizontal: 16,
  },
  emptyTitle: {
    color: colors.text,
    fontSize: 17,
    fontWeight: '600',
  },
  emptyBody: {
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 20,
    textAlign: 'center',
    marginTop: 8,
  },
  noSchedule: {
    color: colors.textSecondary,
    fontSize: 16,
    textAlign: 'center',
    marginTop: 24,
  },
  card: {
    marginTop: 16,
    paddingHorizontal: 16,
    borderRadius: 20,
    backgroundColor: colors.background,
  },
  row: {
    flexDirection: 'row',
  },
  pressed: {
    opacity: 0.7,
  },
  rowBody: {
    flex: 1,
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 8,
  },
  rowDivider: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.divider,
  },
  rowTime: {
    color: colors.textSecondary,
    fontSize: 16,
  },
  rowLabel: {
    flex: 1,
    color: colors.text,
    fontSize: 17,
  },
  detail: {
    gap: 12,
    marginTop: 16,
    padding: 16,
    borderRadius: 20,
    backgroundColor: colors.background,
  },
  detailRow: {
    gap: 4,
  },
  detailLabel: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: '600',
  },
  detailValue: {
    color: colors.text,
    fontSize: 16,
    lineHeight: 22,
  },
  projectRow: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  projectText: {
    flex: 1,
    gap: 4,
  },
});
