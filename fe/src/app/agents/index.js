import { useFocusEffect } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use, useCallback, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  LayoutAnimation,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import AgentForm from '@/components/AgentForm';
import AuthButton from '@/components/AuthButton';
import DrawerScreen from '@/components/DrawerScreen';
import { AgentIcon } from '@/components/HomeIcons';
import PageHeader from '@/components/PageHeader';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import { getAgents } from '@/services/agents';
import { getErrorMessage } from '@/services/auth';

export default function Agents() {
  return (
    <DrawerScreen>
      {(menuButton) => <AgentsContent menuButton={menuButton} />}
    </DrawerScreen>
  );
}

function AgentsContent({ menuButton }) {
  const [user] = use(MyUserContext);
  const token = user?.access_token;
  const [agents, setAgents] = useState(null);
  const [error, setError] = useState('');
  const [formOpen, setFormOpen] = useState(false);

  const loadAgents = useCallback(async () => {
    if (!token) return;
    try {
      setAgents(await getAgents(token));
      setError('');
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [token]);

  useFocusEffect(
    useCallback(() => {
      loadAgents();
    }, [loadAgents])
  );

  const toggleForm = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setFormOpen((open) => !open);
  };

  const handleSaved = async () => {
    await loadAgents();
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setFormOpen(false);
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />
      <PageHeader title="Agent" left={menuButton} />
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
            {error ? <Text style={styles.error}>{error}</Text> : null}
            {agents === null && !error ? <ActivityIndicator color={colors.text} style={styles.loading} /> : null}
            {agents?.length === 0 ? <Text style={styles.empty}>Chưa có Agent nào</Text> : null}
            {agents?.length > 0 ? (
              <View style={styles.card}>
                {agents.map((agent, index) => (
                  <View key={agent.id} style={styles.row}>
                    <AgentIcon size={22} />
                    <View style={[styles.rowBody, index > 0 && styles.rowDivider]}>
                      <Text style={styles.rowLabel} numberOfLines={1}>{agent.name}</Text>
                    </View>
                  </View>
                ))}
              </View>
            ) : null}

            {formOpen ? (
              <>
                <AgentForm onSaved={handleSaved} />
                <View style={styles.cancel}>
                  <AuthButton title="Hủy" variant="secondary" onPress={toggleForm} />
                </View>
              </>
            ) : (
              <AuthButton title="+ Thêm Agent" onPress={toggleForm} />
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  flex: {
    flex: 1,
  },
  cancel: {
    marginTop: 12,
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
  loading: {
    marginBottom: 24,
  },
  error: {
    color: colors.error,
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 24,
  },
  empty: {
    color: colors.textSecondary,
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 24,
  },
  card: {
    marginBottom: 24,
    paddingHorizontal: 16,
    borderRadius: 20,
    backgroundColor: colors.surface,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  rowBody: {
    flex: 1,
    minHeight: 52,
    justifyContent: 'center',
    paddingVertical: 8,
  },
  rowDivider: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.divider,
  },
  rowLabel: {
    color: colors.text,
    fontSize: 17,
  },
});
