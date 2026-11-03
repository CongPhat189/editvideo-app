import { router, useFocusEffect } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use, useCallback, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import AuthButton from '@/components/AuthButton';
import { AgentIcon } from '@/components/HomeIcons';
import PageHeader from '@/components/PageHeader';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import { getAgents } from '@/services/agents';
import { getErrorMessage } from '@/services/auth';

export default function Agents() {
  const [user] = use(MyUserContext);
  const token = user?.access_token;
  const [agents, setAgents] = useState(null);
  const [error, setError] = useState('');

  // Tải lại khi quay về từ form thêm Agent
  useFocusEffect(
    useCallback(() => {
      if (!token) return undefined;
      let active = true;
      getAgents(token)
        .then((items) => {
          if (!active) return;
          setAgents(items);
          setError('');
        })
        .catch((err) => {
          if (active) setError(getErrorMessage(err));
        });
      return () => {
        active = false;
      };
    }, [token])
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />
      <PageHeader title="Agent" />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.page}>
          <AuthButton title="+ Thêm Agent" onPress={() => router.push('/agents/new')} />

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
    paddingTop: 16,
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
    color: colors.textSecondary,
    fontSize: 16,
    textAlign: 'center',
    marginTop: 32,
  },
  card: {
    marginTop: 24,
    paddingHorizontal: 16,
    borderRadius: 20,
    backgroundColor: colors.background,
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
