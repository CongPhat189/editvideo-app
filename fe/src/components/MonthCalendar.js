import { Pressable, StyleSheet, Text, View } from 'react-native';

import { BackIcon, ChevronRightIcon } from '@/components/HomeIcons';
import { colors } from '@/constants/theme';

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

export default function MonthCalendar({ year, month, selectedKey, markedKeys, onSelectDay, onChangeMonth }) {
  const todayKey = toDayKey(new Date());
  const cells = buildCells(year, month);

  return (
    <View>
      <View style={styles.monthRow}>
        <Pressable
          onPress={() => onChangeMonth(-1)}
          style={({ pressed }) => [styles.monthButton, pressed && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel="Tháng trước"
        >
          <BackIcon size={22} />
        </Pressable>
        <Text style={styles.monthTitle}>Tháng {month + 1}, {year}</Text>
        <Pressable
          onPress={() => onChangeMonth(1)}
          style={({ pressed }) => [styles.monthButton, pressed && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel="Tháng sau"
        >
          <ChevronRightIcon size={22} />
        </Pressable>
      </View>

      <View style={styles.grid}>
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
          return (
            <Pressable
              key={key}
              onPress={() => onSelectDay(key)}
              style={styles.cell}
              accessibilityRole="button"
              accessibilityLabel={`Ngày ${day} tháng ${month + 1}${marked ? ', có lịch' : ''}`}
              aria-selected={selected}
            >
              <View style={[styles.day, key === todayKey && styles.today, selected && styles.daySelected]}>
                <Text style={[styles.dayText, selected && styles.dayTextSelected]}>{day}</Text>
                {marked ? <View style={[styles.dot, selected && styles.dotSelected]} /> : null}
              </View>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  monthRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  monthButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 22,
  },
  pressed: {
    opacity: 0.7,
  },
  monthTitle: {
    color: colors.text,
    fontSize: 17,
    fontWeight: '600',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  cell: {
    width: `${100 / 7}%`,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  weekday: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: '600',
  },
  day: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  today: {
    borderColor: colors.divider,
  },
  daySelected: {
    backgroundColor: colors.primary,
  },
  dayText: {
    color: colors.text,
    fontSize: 16,
  },
  dayTextSelected: {
    color: colors.onPrimary,
    fontWeight: '600',
  },
  dot: {
    position: 'absolute',
    bottom: 4,
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: colors.accent,
  },
  dotSelected: {
    backgroundColor: colors.onPrimary,
  },
});
