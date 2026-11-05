import { useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import { FadeIn } from '@/components/Motion';
import { useThemeColors, useThemeStyles } from '@/constants/theme';

export default function AuthField({ label, icon, error, ref, onFocus, onBlur, ...inputProps }) {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);
  const [focused, setFocused] = useState(false);

  return (
    <View style={styles.field}>
      <Text style={[styles.label, focused && styles.labelFocused]}>{label}</Text>
      <View style={[styles.inputRow, focused && styles.inputRowFocused, error && styles.inputRowError]}>
        {icon}
        <TextInput
          ref={ref}
          style={styles.input}
          placeholderTextColor={colors.textMuted}
          selectionColor={colors.primary}
          cursorColor={colors.primary}
          accessibilityLabel={label}
          onFocus={(event) => {
            setFocused(true);
            onFocus?.(event);
          }}
          onBlur={(event) => {
            setFocused(false);
            onBlur?.(event);
          }}
          {...inputProps}
        />
      </View>
      {error ? <FadeIn key={error} distance={-4} duration={280}><Text style={styles.error}>{error}</Text></FadeIn> : null}
    </View>
  );
}

const createStyles = (colors) => StyleSheet.create({
  field: {
    marginBottom: 18,
  },
  label: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 0.4,
    marginBottom: 8,
    marginLeft: 2,
  },
  labelFocused: {
    color: colors.gold,
  },
  inputRow: {
    height: 52,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  inputRowFocused: {
    borderColor: colors.goldBorder,
    backgroundColor: colors.surfaceRaised,
  },
  inputRowError: {
    borderColor: colors.errorBorder,
    backgroundColor: colors.errorSoft,
  },
  input: {
    flex: 1,
    height: '100%',
    color: colors.text,
    fontSize: 16,
    outlineStyle: 'none',
  },
  error: {
    color: colors.error,
    fontSize: 12.5,
    marginTop: 6,
    marginLeft: 2,
  },
});
