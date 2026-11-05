import { Pressable, StyleSheet, Text, View } from 'react-native';

import { BackIcon, ChevronRightIcon } from '@/components/HomeIcons';
import { FadeIn, PopIn } from '@/components/Motion';
import { fonts, useThemeColors, useThemeStyles } from '@/constants/theme';

const WEEKDAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];

const pad = (value) => String(value).padStart(2, '0');

export const toDayKey = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;

const buildCells = (year, month) => {
  const firstWeekday = (new Date(year, month, 1).getDay() + 6) % 7; // Tuần bắt đầu từ thứ Hai
  const dayCount = new Date(year, month + 1, 0).getDate();
  const cells = Array.from({ length: firstWeekday }, () => null);
  for (let day = 1; day <= dayCount; day += 1) cells.push(day);
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
};

export default function MonthCalendar({ year, month, selectedKey, minKey, markedKeys, onSelectDay, onChangeMonth }) {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

  const todayKey = toDayKey(new Date());
  const cells = buildCells(year, month);

  return (
    <View style={styles.calendar}>
      <View style={styles.monthRow}>
        <Pressable
          onPress={() => onChangeMonth(-1)}
          style={({ pressed }) => [styles.monthButton, pressed && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel="Tháng trước"
        >
          <BackIcon size={19} color={colors.textSecondary} />
        </Pressable>
        <Text style={styles.monthTitle}>Tháng {month + 1}, {year}</Text>
        <Pressable
          onPress={() => onChangeMonth(1)}
          style={({ pressed }) => [styles.monthButton, pressed && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel="Tháng sau"
        >
          <ChevronRightIcon size={19} color={colors.textSecondary} />
        </Pressable>
      </View>

      <FadeIn key={`${year}-${month}`} style={styles.grid} distance={8} duration={380}>
        {WEEKDAYS.map((weekday) => (
          <View key={weekday} style={styles.cell}>
            <Text style={styles.weekday}>{weekday}</Text>
          </View>
        ))}
        {cells.map((day, index) => {
          if (day === null) return <View key={`empty-${index}`} style={styles.cell} />;
          const key = `${year}-${pad(month + 1)}-${pad(day)}`;
          const selected = key === selectedKey;
          const marked = markedKeys.has(key);
          const disabled = Boolean(minKey) && key < minKey;
          return (
            <Pressable
              key={key}
              onPress={() => onSelectDay(key)}
              disabled={disabled}
              style={styles.cell}
              accessibilityRole="button"
              accessibilityLabel={`Ngày ${day} tháng ${month + 1}${marked ? ', có lịch' : ''}`}
              accessibilityState={{ disabled }}
              aria-selected={selected}
            >
              <PopIn
                key={selected ? 'selected' : 'idle'}
                from={selected ? 0.7 : 1}
                style={[styles.day, key === todayKey && styles.today, selected && styles.daySelected, disabled && styles.dayDisabled]}
              >
                <Text style={[styles.dayText, key === todayKey && styles.dayTextToday, selected && styles.dayTextSelected]}>{day}</Text>
                {marked ? <View style={[styles.dot, selected && styles.dotSelected]} /> : null}
              </PopIn>
            </Pressable>
          );
        })}
      </FadeIn>
    </View>
  );
}

const createStyles = (colors) => StyleSheet.create({
  calendar: {
    padding: 12,
    paddingBottom: 10,
    borderRadius: 24,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.card,
  },
  monthRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  monthButton: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 20,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
  },
  pressed: {
    opacity: 0.7,
  },
  monthTitle: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 19,
    fontWeight: '600',
    letterSpacing: 0.2,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  cell: {
    width: `${100 / 7}%`,
    minHeight: 46,
    alignItems: 'center',
    justifyContent: 'center',
  },
  weekday: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1,
  },
  day: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  today: {
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
  },
  daySelected: {
    borderColor: colors.gold,
    backgroundColor: colors.primary,
  },
  dayDisabled: {
    opacity: 0.28,
  },
  dayText: {
    color: colors.text,
    fontSize: 15.5,
    fontVariant: ['tabular-nums'],
  },
  dayTextToday: {
    color: colors.gold,
    fontWeight: '700',
  },
  dayTextSelected: {
    color: colors.onPrimary,
    fontWeight: '700',
  },
  dot: {
    position: 'absolute',
    bottom: 4,
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.gold,
  },
  dotSelected: {
    backgroundColor: colors.onPrimary,
  },
});
