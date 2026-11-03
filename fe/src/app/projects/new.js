import { router, useFocusEffect } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use, useCallback, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import AuthButton from '@/components/AuthButton';
import AuthField from '@/components/AuthField';
import { AgentIcon, CheckIcon, FolderIcon } from '@/components/HomeIcons';
import PageHeader from '@/components/PageHeader';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import { getAgents } from '@/services/agents';
import { getErrorMessage } from '@/services/auth';
import { createProject } from '@/services/projects';

const MAX_NAME_LENGTH = 255;

export default function NewProject() {
  const [user] = use(MyUserContext);
  const token = user?.access_token;
  const [name, setName] = useState('');
  const [nameError, setNameError] = useState('');
  const [agents, setAgents] = useState(null);
  const [agentId, setAgentId] = useState(null);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);

  // Tải lại khi quay về từ form thêm Agent
  useFocusEffect(
    useCallback(() => {
      if (!token) return undefined;
      let active = true;
      getAgents(token)
        .then((items) => {
          if (!active) return;
          setAgents(items);
          setAgentId((current) => current ?? items[0]?.id ?? null);
        })
        .catch((error) => {
          if (!active) return;
          setAgents([]);
          setFormError(getErrorMessage(error));
        });
      return () => {
        active = false;
      };
    }, [token])
  );

  const handleCreate = async () => {
    const trimmedName = name.trim();
    setNameError(trimmedName ? '' : 'Vui lòng nhập tên dự án');
    setFormError('');
    if (!trimmedName) return;
    if (!agentId) {
      setFormError('Cần có một Agent để tạo dự án');
      return;
    }

    setSaving(true);
    try {
      const project = await createProject(token, trimmedName, agentId);
      router.replace(`/projects/${project.id}`);
    } catch (error) {
      setFormError(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />
      <PageHeader title="Dự án mới" />
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
            <AuthField
              label="Tên dự án"
              icon={<FolderIcon size={20} color={colors.textMuted} />}
              error={nameError}
              value={name}
              onChangeText={setName}
              placeholder="Nhập tên dự án"
              maxLength={MAX_NAME_LENGTH}
              returnKeyType="done"
              onSubmitEditing={handleCreate}
            />

            <Text style={styles.sectionTitle}>Agent</Text>
            {agents === null ? <ActivityIndicator color={colors.text} style={styles.loading} /> : null}
            {agents?.length === 0 ? (
              <View style={styles.noAgents}>
                <Text style={styles.noAgentsText}>Bạn chưa có Agent nào. Hãy thêm Agent trước khi tạo dự án.</Text>
                <AuthButton title="+ Thêm Agent" variant="secondary" onPress={() => router.push('/agents/new')} />
              </View>
            ) : null}
            {agents?.length > 0 ? (
              <View style={styles.card}>
                {agents.map((agent, index) => (
                  <Pressable
                    key={agent.id}
                    onPress={() => setAgentId(agent.id)}
                    style={({ pressed }) => [styles.agentRow, pressed && styles.pressed]}
                    accessibilityRole="radio"
                    accessibilityLabel={agent.name}
                    aria-checked={agent.id === agentId}
                  >
                    <AgentIcon size={22} />
                    <View style={[styles.agentBody, index > 0 && styles.agentDivider]}>
                      <Text style={styles.agentName} numberOfLines={1}>{agent.name}</Text>
                      {agent.id === agentId ? <CheckIcon size={20} /> : null}
                    </View>
                  </Pressable>
                ))}
              </View>
            ) : null}

            {formError ? <Text style={styles.formError}>{formError}</Text> : null}
            <View style={styles.submit}>
              <AuthButton title="Tạo dự án" onPress={handleCreate} loading={saving} />
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.backgroundDeep,
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
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  loading: {
    marginVertical: 16,
  },
  noAgents: {
    gap: 12,
  },
  noAgentsText: {
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 20,
  },
  card: {
    paddingHorizontal: 16,
    borderRadius: 20,
    backgroundColor: colors.background,
  },
  agentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  pressed: {
    opacity: 0.7,
  },
  agentBody: {
    flex: 1,
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 8,
  },
  agentDivider: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.divider,
  },
  agentName: {
    flex: 1,
    color: colors.text,
    fontSize: 17,
  },
  formError: {
    color: colors.error,
    fontSize: 14,
    textAlign: 'center',
    marginTop: 16,
  },
  submit: {
    marginTop: 24,
  },
});
