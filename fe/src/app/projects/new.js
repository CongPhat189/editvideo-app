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
import DrawerScreen from '@/components/DrawerScreen';
import { AgentIcon, CheckIcon, ClapperIcon } from '@/components/HomeIcons';
import { Eyebrow } from '@/components/Luxe';
import { FadeIn, PopIn, stagger } from '@/components/Motion';
import PageHeader from '@/components/PageHeader';
import { MyUserContext } from '@/config/Contexts';
import { fonts, useThemeColors, useThemeStyles } from '@/constants/theme';
import { getAgents } from '@/services/agents';
import { getErrorMessage } from '@/services/auth';
import { createProject } from '@/services/projects';

const MAX_NAME_LENGTH = 255;

export default function NewProject() {
  return (
    <DrawerScreen>
      {(menuButton) => <NewProjectContent menuButton={menuButton} />}
    </DrawerScreen>
  );
}

function NewProjectContent({ menuButton }) {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

  const [user] = use(MyUserContext);
  const token = user?.access_token;
  const [name, setName] = useState('');
  const [nameError, setNameError] = useState('');
  const [agents, setAgents] = useState(null);
  const [agentId, setAgentId] = useState(null);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);

  // Tải lại khi quay về từ form thêm Agen
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
      <StatusBar style={colors.statusBar} />
      <PageHeader title="Dự án mới" left={menuButton} />
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
            <FadeIn style={styles.intro}>
              <Eyebrow>Dự án mới</Eyebrow>
              <Text style={styles.introTitle}>Khởi tạo một video mới</Text>
              <Text style={styles.introText}>Đặt tên cho dự án và chọn Agent sẽ đồng hành cùng bạn.</Text>
            </FadeIn>

            <FadeIn delay={100}>
            <AuthField
              label="Tên dự án"
              icon={<ClapperIcon size={20} color={colors.textMuted} />}
              error={nameError}
              value={name}
              onChangeText={setName}
              placeholder="Nhập tên dự án"
              maxLength={MAX_NAME_LENGTH}
              returnKeyType="done"
              onSubmitEditing={handleCreate}
            />
            </FadeIn>

            <FadeIn delay={180}><Text style={styles.sectionTitle}>Chọn Agent</Text></FadeIn>
            {agents === null ? <ActivityIndicator color={colors.gold} style={styles.loading} /> : null}
            {agents?.length === 0 ? (
              <FadeIn style={styles.noAgents} delay={220}>
                <Text style={styles.noAgentsText}>Bạn chưa có Agent nào. Hãy thêm Agent trước khi tạo dự án.</Text>
                <AuthButton title="+ Thêm Agent" variant="secondary" onPress={() => router.push('/agents/new')} />
              </FadeIn>
            ) : null}
            {agents?.length > 0 ? (
              <FadeIn style={styles.card} delay={220}>
                {agents.map((agent, index) => (
                  <FadeIn key={agent.id} delay={stagger(index, 60, 280)} axis="x" distance={14}>
                  <Pressable
                    onPress={() => setAgentId(agent.id)}
                    style={({ pressed }) => [
                      styles.agentRow,
                      index > 0 && styles.agentDivider,
                      agent.id === agentId && styles.agentRowSelected,
                      pressed && styles.pressed,
                    ]}
                    accessibilityRole="radio"
                    accessibilityLabel={agent.name}
                    aria-checked={agent.id === agentId}
                  >
                    <View style={[styles.agentIcon, agent.id === agentId && styles.agentIconSelected]}>
                      <AgentIcon size={20} color={agent.id === agentId ? colors.gold : colors.textSecondary} />
                    </View>
                    <View style={styles.agentBody}>
                      <Text style={styles.agentName} numberOfLines={1}>{agent.name}</Text>
                      <View style={[styles.radio, agent.id === agentId && styles.radioSelected]}>
                        {agent.id === agentId ? (
                          <PopIn key="checked"><CheckIcon size={13} color={colors.onPrimary} /></PopIn>
                        ) : null}
                      </View>
                    </View>
                  </Pressable>
                  </FadeIn>
                ))}
              </FadeIn>
            ) : null}

            {formError ? <Text style={styles.formError}>{formError}</Text> : null}
            <FadeIn style={styles.submit} delay={360}>
              <AuthButton title="Tạo dự án" onPress={handleCreate} loading={saving} />
            </FadeIn>
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
  },
  intro: {
    marginBottom: 26,
    marginTop: 4,
  },
  introTitle: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 26,
    lineHeight: 33,
    fontWeight: '600',
    marginTop: 8,
  },
  introText: {
    color: colors.textSecondary,
    fontSize: 14.5,
    lineHeight: 21,
    marginTop: 6,
  },
  sectionTitle: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 0.4,
    marginBottom: 8,
    marginTop: 6,
    marginLeft: 2,
  },
  loading: {
    marginVertical: 16,
  },
  noAgents: {
    gap: 14,
    padding: 18,
    borderRadius: 20,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.card,
  },
  noAgentsText: {
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 21,
  },
  card: {
    padding: 6,
    borderRadius: 22,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.card,
  },
  agentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingHorizontal: 12,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  agentRowSelected: {
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
  },
  pressed: {
    opacity: 0.75,
  },
  agentIcon: {
    width: 38,
    height: 38,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
    backgroundColor: colors.surface,
  },
  agentIconSelected: {
    backgroundColor: colors.surfaceRaised,
  },
  agentBody: {
    flex: 1,
    minHeight: 60,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 8,
  },
  agentDivider: {
    marginTop: 4,
  },
  agentName: {
    flex: 1,
    color: colors.text,
    fontSize: 16,
    fontWeight: '500',
  },
  radio: {
    width: 22,
    height: 22,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 11,
    borderWidth: 1.5,
    borderColor: colors.borderStrong,
  },
  radioSelected: {
    borderColor: colors.gold,
    backgroundColor: colors.gold,
  },
  formError: {
    color: colors.error,
    fontSize: 13.5,
    textAlign: 'center',
    marginTop: 16,
  },
  submit: {
    marginTop: 28,
  },
});
