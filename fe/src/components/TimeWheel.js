import { memo, useCallback, useRef, useState } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';

import { useThemeStyles } from '@/constants/theme';

export const ROW_HEIGHT = 44;
export const CENTER_ROW = 3;
const VISIBLE_ROWS = CENTER_ROW * 2 + 1;
export const WHEEL_HEIGHT = ROW_HEIGHT * VISIBLE_ROWS;
// Đủ dài để vuốt như vòng tròn 23 -> 00 -> 01, FlatList chỉ dựng các dòng đang thấy
const TOTAL_ROWS = 2400;
const START_ROW = TOTAL_ROWS / 2;
const ROWS = Array.from({ length: TOTAL_ROWS }, (_, index) => index);

// Các dòng nằm trên mặt trụ: càng xa dòng giữa càng nghiêng, mờ và dồn về giữa
const DISTANCES = [-4, -3, -2, -1, 0, 1, 2, 3, 4];
const ROTATE_X = DISTANCES.map((distance) => `${distance * 20}deg`);
const TRANSLATE_Y = [-52, -23, -7, -1, 0, 1, 7, 23, 52];
const OPACITY = [0, 0.25, 0.42, 0.62, 1, 0.62, 0.42, 0.25, 0];

const pad = (value) => String(value).padStart(2, '0');
const keyExtractor = (row) => String(row);
const getItemLayout = (_, index) => ({ length: ROW_HEIGHT, offset: ROW_HEIGHT * index, index });

const WheelRow = memo(function WheelRow({ row, count, scrollY }) {
  const styles = useThemeStyles(createStyles);

  const center = (row - CENTER_ROW) * ROW_HEIGHT;
  const inputRange = DISTANCES.map((distance) => center + distance * ROW_HEIGHT);
  const animate = (outputRange) => scrollY.interpolate({ inputRange, outputRange, extrapolate: 'clamp' });

  return (
    <Animated.View
      style={[
        styles.row,
        {
          opacity: animate(OPACITY),
          transform: [{ perspective: 600 }, { translateY: animate(TRANSLATE_Y) }, { rotateX: animate(ROTATE_X) }],
        },
      ]}
    >
      <Text style={styles.label}>{pad(row % count)}</Text>
    </Animated.View>
  );
});

// Giữ vị trí bánh xe ngoài state vì nó đổi theo từng khung hình khi vuốt. onChange phải là hàm ổn định
const createWheel = ({ count, initialValue, onChange, setValue }) => {
  const startTop = START_ROW + initialValue - CENTER_ROW;
  const scrollY = new Animated.Value(startTop * ROW_HEIGHT);
  let top = startTop;
  let value = initialValue;

  return {
    scrollY,
    startTop,
    nextOffset: (delta) => (top + delta) * ROW_HEIGHT,
    onScroll: Animated.event([{ nativeEvent: { contentOffset: { y: scrollY } } }], {
      useNativeDriver: true,
      listener: (event) => {
        // Android có thể báo vị trí 0 lúc mới dựng, người dùng thì không vuốt tới được đầu danh sách
        const offsetY = event.nativeEvent.contentOffset.y;
        if (offsetY === 0) return;
        top = Math.round(offsetY / ROW_HEIGHT);
        const next = (top + CENTER_ROW) % count;
        if (next === value) return;
        value = next;
        setValue(next);
        onChange(next);
      },
    }),
  };
};

export default function TimeWheel({ count, initialValue, label, onChange }) {
  const styles = useThemeStyles(createStyles);

  const listRef = useRef(null);
  const [value, setValue] = useState(initialValue);
  const [wheel] = useState(() => createWheel({ count, initialValue, onChange, setValue }));
  const { scrollY } = wheel;

  const renderItem = useCallback(
    ({ item }) => <WheelRow row={item} count={count} scrollY={scrollY} />,
    [count, scrollY]
  );

  const handleAccessibilityAction = ({ nativeEvent }) => {
    const delta = nativeEvent.actionName === 'increment' ? 1 : -1;
    listRef.current?.scrollToOffset({ offset: wheel.nextOffset(delta), animated: true });
  };

  return (
    <View
      style={styles.wheel}
      accessible
      accessibilityRole="adjustable"
      accessibilityLabel={label}
      accessibilityValue={{ text: pad(value) }}
      accessibilityActions={[{ name: 'increment' }, { name: 'decrement' }]}
      onAccessibilityAction={handleAccessibilityAction}
    >
      <Animated.FlatList
        ref={listRef}
        data={ROWS}
        renderItem={renderItem}
        keyExtractor={keyExtractor}
        getItemLayout={getItemLayout}
        initialScrollIndex={wheel.startTop}
        initialNumToRender={VISIBLE_ROWS + 2}
        windowSize={11}
        removeClippedSubviews={false}
        snapToInterval={ROW_HEIGHT}
        decelerationRate="fast"
        bounces={false}
        overScrollMode="never"
        showsVerticalScrollIndicator={false}
        scrollEventThrottle={16}
        onScroll={wheel.onScroll}
      />
    </View>
  );
}

const createStyles = (colors) => StyleSheet.create({
  wheel: {
    width: 96,
    height: WHEEL_HEIGHT,
    overflow: 'hidden',
  },
  row: {
    height: ROW_HEIGHT,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    color: colors.text,
    fontSize: 30,
    fontWeight: '300',
    letterSpacing: 1,
    fontVariant: ['tabular-nums'],
  },
});
