import { StatusBar } from 'expo-status-bar';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AmbientGlow, BrandMark, Eyebrow, Ornament } from '@/components/Luxe';
import { Breathing, FadeIn } from '@/components/Motion';
import { fonts, useThemeColors, useThemeStyles } from '@/constants/theme';

export default function AuthScreen({ title, subtitle, footer, children }) {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style={colors.statusBar} />
      <AmbientGlow height={520} intensity={1.2} />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.inner}>
            <FadeIn style={styles.header} distance={18}>
              <Breathing style={styles.logoHalo} duration={3400} scaleTo={1.05}>
                <BrandMark size={68} shimmer />
              </Breathing>
              <Eyebrow align="center" style={styles.eyebrow}>AI Video Studio</Eyebrow>
              <Text style={styles.title}>{title}</Text>
              <Ornament width={96} style={styles.ornament} />
              <Text style={styles.subtitle}>{subtitle}</Text>
            </FadeIn>
            <FadeIn style={styles.form} delay={140} distance={24}>{children}</FadeIn>
            <FadeIn style={styles.footer} delay={300}>{footer}</FadeIn>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const createStyles = (colors) => StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  flex: {
    flex: 1,
  },
  content: {
    flexGrow: 1,
    paddingHorizontal: 20,
    paddingTop: 44,
    paddingBottom: 20,
  },
  inner: {
    flexGrow: 1,
    width: '100%',
    maxWidth: 440,
    alignSelf: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 32,
  },
  logoHalo: {
    padding: 6,
    borderRadius: 30,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
    marginBottom: 22,
    shadowColor: colors.glow,
    shadowOpacity: 0.35,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  eyebrow: {
    marginBottom: 10,
  },
  title: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 32,
    lineHeight: 40,
    fontWeight: '600',
    letterSpacing: 0.2,
    textAlign: 'center',
  },
  ornament: {
    marginTop: 14,
    marginBottom: 14,
  },
  subtitle: {
    color: colors.textSecondary,
    fontSize: 15,
    lineHeight: 22,
    textAlign: 'center',
    maxWidth: 320,
  },
  form: {
    padding: 20,
    paddingBottom: 22,
    borderRadius: 26,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.card,
    shadowColor: colors.shadow,
    shadowOpacity: 0.18,
    shadowRadius: 30,
    shadowOffset: { width: 0, height: 14 },
    elevation: 4,
  },
  footer: {
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'flex-end',
    paddingTop: 28,
  },
});
