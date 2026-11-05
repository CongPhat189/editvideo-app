import { router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import AgentForm from '@/components/AgentForm';
import PageHeader from '@/components/PageHeader';
import { useThemeColors, useThemeStyles } from '@/constants/theme';

// Trang riêng để thêm Agent ngay từ form tạo dự án; trang Agent thì hiện form ngay trong danh sách
export default function NewAgent() {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style={colors.statusBar} />
      <PageHeader title="Thêm Agent" />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.page}>
            <AgentForm onSaved={() => router.back()} />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const createStyles = (colors) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  flex: {
    flex: 1,
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
    padding: 20,
    borderRadius: 24,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.card,
  },
});
