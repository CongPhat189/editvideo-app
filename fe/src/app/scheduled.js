import { router, useFocusEffect } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use, useCallback, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import DrawerScreen from '@/components/DrawerScreen';
import { MessageAttachments } from '@/components/ChatAttachments';
import { ChevronRightIcon, ClockIcon } from '@/components/HomeIcons';
import { Eyebrow } from '@/components/Luxe';
import { Breathing, FadeIn, stagger } from '@/components/Motion';
import MonthCalendar, { toDayKey } from '@/components/MonthCalendar';
import PageHeader from '@/components/PageHeader';
import { MyUserContext } from '@/config/Contexts';
import { fonts, useThemeColors, useThemeStyles } from '@/constants/theme';
import { getErrorMessage } from '@/services/auth';
import { getProjects } from '@/services/projects';
import { formatScheduleTime, getScheduleDayKey, getSchedules } from '@/services/schedules';

const DetailRow = ({ label, value }) => {
  const styles = useThemeStyles(createStyles);
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={styles.detailValue} selectable>{value}</Text>
    </View>
  );
};

const getScheduleAttachments = (schedule) => {
  const attachments = schedule.attachments ?? schedule.media ?? schedule.files;
  if (Array.isArray(attachments)) {
    return attachments.map((file, index) => ({
      ...file,
      id: file.id ?? `${schedule.id}-attachment-${index}`,
      url: file.url ?? file.uri ?? file.image_url,
      mime_type: file.mime_type ?? file.mimeType ?? 'image/jpeg',
      file_name: file.file_name ?? file.fileName ?? `Ảnh ${index + 1}`,
    }));
  }

  const imageUrls = schedule.image_urls ?? schedule.images ?? (schedule.image_url ? [schedule.image_url] : []);
  if (!Array.isArray(imageUrls)) return [];
  return imageUrls.map((image, index) => ({
    id: `${schedule.id}-image-${index}`,
    url: typeof image === 'string' ? image : image.url ?? image.uri,
    mime_type: typeof image === 'object' ? image.mime_type ?? image.mimeType ?? 'image/jpeg' : 'image/jpeg',
    file_name: typeof image === 'object' ? image.file_name ?? image.fileName ?? `Ảnh ${index + 1}` : `Ảnh ${index + 1}`,
  })).filter((image) => image.url);
};

export default function Scheduled() {
  return (
    <DrawerScreen>
      {(menuButton) => <ScheduledContent menuButton={menuButton} />}
    </DrawerScreen>
  );
}

function ScheduledContent({ menuButton }) {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

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
  const selectedAttachments = selected ? getScheduleAttachments(selected) : [];

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
      <StatusBar style={colors.statusBar} />
      <PageHeader title="Đã lên lịch" left={menuButton} />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.page}>
          <FadeIn distance={18}>
            <MonthCalendar
              year={view.year}
              month={view.month}
              selectedKey={selectedKey}
              markedKeys={markedKeys}
              onSelectDay={selectDay}
              onChangeMonth={changeMonth}
            />
          </FadeIn>

          {error ? <Text style={styles.error}>{error}</Text> : null}
          {schedules === null ? <ActivityIndicator color={colors.gold} style={styles.loading} /> : null}

          {schedules?.length === 0 && !error ? (
            <FadeIn style={styles.empty} delay={150}>
              <Breathing style={styles.emptyIcon} duration={3200} scaleTo={1.06}><ClockIcon size={26} color={colors.gold} /></Breathing>
              <Text style={styles.emptyTitle}>Chưa có lịch nào</Text>
              <Text style={styles.emptyBody}>Mở một dự án và đặt lịch ngay trong Chat, lịch sẽ hiện ở đây.</Text>
            </FadeIn>
          ) : null}

          {schedules?.length > 0 && daySchedules.length === 0 ? (
            <FadeIn key={`none-${selectedKey}`}><Text style={styles.noSchedule}>Không có lịch trong ngày này</Text></FadeIn>
          ) : null}

          {daySchedules.length > 0 ? (
            <FadeIn key={`day-${selectedKey}`} style={styles.card} delay={80}>
              {daySchedules.map((schedule, index) => (
                <FadeIn key={schedule.id} delay={stagger(index, 60, 140)} axis="x" distance={14}>
                <Pressable
                  onPress={() => setSelectedId(schedule.id)}
                  style={({ pressed }) => [styles.row, pressed && styles.pressed]}
                  accessibilityRole="button"
                  accessibilityLabel={schedule.task_name}
                  aria-selected={schedule.id === selectedId}
                >
                  <View style={[styles.rowBody, index > 0 && styles.rowDivider]}>
                    <View style={[styles.timeChip, schedule.id === selectedId && styles.timeChipSelected]}>
                      <Text style={[styles.rowTime, schedule.id === selectedId && styles.rowTimeSelected]}>{formatScheduleTime(schedule).slice(11)}</Text>
                    </View>
                    <Text style={styles.rowLabel} numberOfLines={1}>{schedule.task_name}</Text>
                    <ChevronRightIcon size={18} color={schedule.id === selectedId ? colors.gold : colors.textMuted} />
                  </View>
                </Pressable>
                </FadeIn>
              ))}
            </FadeIn>
          ) : null}

          {selected ? (
            <FadeIn key={`detail-${selected.id}`} style={styles.detail} distance={20}>
              <Eyebrow>Chi tiết lịch đăng</Eyebrow>
              <DetailRow label="Tên" value={selected.task_name} />
              <DetailRow label="Thời gian" value={formatScheduleTime(selected)} />
              {selected.platforms.length > 0 ? (
                <DetailRow label="Nền tảng" value={selected.platforms.join(', ')} />
              ) : null}
              {selected.content || selectedAttachments.length > 0 ? (
                <View style={styles.contentSection}>
                  <Text style={styles.detailLabel}>Nội dung</Text>
                  {selected.content ? <Text style={styles.detailValue} selectable>{selected.content}</Text> : null}
                  {selectedAttachments.length > 0 ? <MessageAttachments attachments={selectedAttachments} /> : null}
                </View>
              ) : null}
              <Pressable
                onPress={() => router.replace(`/projects/${selected.conversation_id}`)}
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
                {projectName ? <ChevronRightIcon size={18} color={colors.gold} /> : null}
              </Pressable>
            </FadeIn>
          ) : null}
        </View>
      </ScrollView>
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
    paddingTop: 10,
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
    fontSize: 13.5,
    textAlign: 'center',
    marginTop: 20,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.errorBorder,
    backgroundColor: colors.errorSoft,
    overflow: 'hidden',
  },
  empty: {
    alignItems: 'center',
    marginTop: 28,
    paddingHorizontal: 16,
  },
  emptyIcon: {
    width: 60,
    height: 60,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
    marginBottom: 16,
  },
  emptyTitle: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 20,
    fontWeight: '600',
  },
  emptyBody: {
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 21,
    textAlign: 'center',
    marginTop: 8,
    maxWidth: 320,
  },
  noSchedule: {
    color: colors.textMuted,
    fontSize: 14.5,
    fontStyle: 'italic',
    textAlign: 'center',
    marginTop: 24,
  },
  card: {
    marginTop: 16,
    padding: 6,
    borderRadius: 22,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.card,
  },
  row: {
    flexDirection: 'row',
  },
  pressed: {
    opacity: 0.7,
  },
  rowBody: {
    flex: 1,
    minHeight: 58,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 8,
    paddingHorizontal: 10,
  },
  rowDivider: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderStrong,
  },
  timeChip: {
    minWidth: 62,
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
  },
  timeChipSelected: {
    borderColor: colors.gold,
    backgroundColor: colors.gold,
  },
  rowTime: {
    color: colors.gold,
    fontSize: 14,
    fontWeight: '700',
    fontVariant: ['tabular-nums'],
  },
  rowTimeSelected: {
    color: colors.onPrimary,
  },
  rowLabel: {
    flex: 1,
    color: colors.text,
    fontSize: 15.5,
    fontWeight: '500',
  },
  detail: {
    gap: 16,
    marginTop: 16,
    padding: 20,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.card,
  },
  detailRow: {
    gap: 5,
  },
  contentSection: {
    gap: 8,
  },
  detailLabel: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  detailValue: {
    color: colors.text,
    fontSize: 15.5,
    lineHeight: 23,
  },
  projectRow: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingTop: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderStrong,
  },
  projectText: {
    flex: 1,
    gap: 5,
  },
});
