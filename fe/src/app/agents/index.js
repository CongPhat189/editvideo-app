import { useFocusEffect } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use, useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  LayoutAnimation,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import AgentForm from '@/components/AgentForm';
import AuthButton from '@/components/AuthButton';
import DrawerScreen from '@/components/DrawerScreen';
import {
  AgentIcon,
  PencilIcon,
  PluginIcon,
  TrashIcon,
} from '@/components/HomeIcons';
import { Ornament } from '@/components/Luxe';
import { Breathing, FadeIn, stagger } from '@/components/Motion';
import PageHeader from '@/components/PageHeader';
import { MyUserContext } from '@/config/Contexts';
import { fonts, useThemeColors, useThemeStyles } from '@/constants/theme';
import {
  deleteAgent,
  getAgentErrorMessage,
  getAgentsByUser,
  testSavedAgentConnection,
} from '@/services/agents';

export default function Agents() {
  return (
    <DrawerScreen>
      {(menuButton) => <AgentsContent menuButton={menuButton} />}
    </DrawerScreen>
  );
}

function AgentsContent({ menuButton }) {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

  const [user] = use(MyUserContext);
  const token = user?.access_token;
  const userId = user?.id;

  const [agents, setAgents] = useState(null);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState(null);

  // Lưu trạng thái test kết nối cho từng agent: { [agentId]: { ok: bool, message: str } }
  const [testResults, setTestResults] = useState({});
  const [testingId, setTestingId] = useState(null);

  const loadAgents = useCallback(
    async (isPullRefresh = false) => {
      if (!token) return;
      if (isPullRefresh) setRefreshing(true);

      try {
        const data = await getAgentsByUser(token, userId);
        setAgents(data || []);
        setError('');
      } catch (err) {
        setError(getAgentErrorMessage(err));
      } finally {
        setRefreshing(false);
      }
    },
    [token, userId]
  );

  useFocusEffect(
    useCallback(() => {
      loadAgents();
    }, [loadAgents])
  );

  const toggleForm = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setEditingAgent(null);
    setFormOpen((open) => !open);
  };

  const handleEditAgent = (agent) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setEditingAgent(agent);
    setFormOpen(true);
  };

  const handleDeleteAgent = (agent) => {
    Alert.alert(
      'Xác nhận xóa',
      `Bạn có chắc chắn muốn xóa agent "${agent.name}" không?`,
      [
        { text: 'Hủy', style: 'cancel' },
        {
          text: 'Xóa',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteAgent(token, agent.id);
              await loadAgents();
            } catch (err) {
              Alert.alert('Lỗi xóa Agent', getAgentErrorMessage(err));
            }
          },
        },
      ]
    );
  };

  const handleTestAgent = async (agent) => {
    setTestingId(agent.id);
    setTestResults((prev) => ({ ...prev, [agent.id]: null }));

    try {
      const res = await testSavedAgentConnection(token, agent.id);
      LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
      setTestResults((prev) => ({
        ...prev,
        [agent.id]: {
          ok: res.ok,
          message: res.ok ? 'Kết nối GoClaw thành công' : (res.message || 'Không kết nối được GoClaw'),
        },
      }));
    } catch (err) {
      LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
      setTestResults((prev) => ({
        ...prev,
        [agent.id]: {
          ok: false,
          message: getAgentErrorMessage(err),
        },
      }));
    } finally {
      setTestingId(null);
    }
  };

  const handleSaved = async () => {
    await loadAgents();
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setFormOpen(false);
    setEditingAgent(null);
  };

  const handleCancelForm = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setFormOpen(false);
    setEditingAgent(null);
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style={colors.statusBar} />
      <PageHeader title="Agent" left={menuButton} />

      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => loadAgents(true)}
              tintColor={colors.gold}
              colors={[colors.gold]}
            />
          }
        >
          <View style={styles.page}>
            {error ? <Text style={styles.error}>{error}</Text> : null}

            {agents === null && !error ? (
              <ActivityIndicator color={colors.gold} style={styles.loading} />
            ) : null}

            {/* Form Thêm mới / Chỉnh sửa */}
            {formOpen ? (
              <FadeIn style={styles.formContainer} distance={18}>
                <AgentForm
                  agent={editingAgent}
                  onSaved={handleSaved}
                  onCancel={handleCancelForm}
                />
              </FadeIn>
            ) : (
              <FadeIn style={styles.topAction}>
                <AuthButton title="+ Thêm Agent" onPress={toggleForm} />
              </FadeIn>
            )}

            {/* Trạng thái trống */}
            {agents?.length === 0 && !formOpen ? (
              <FadeIn style={styles.emptyContainer} delay={120}>
                <Breathing style={styles.emptyIconBox} duration={3200} scaleTo={1.06}>
                  <AgentIcon size={32} color={colors.gold} />
                </Breathing>
                <Text style={styles.emptyTitle}>Chưa có Agent nào</Text>
                <Ornament width={80} style={styles.emptyOrnament} />
                <Text style={styles.emptySubtitle}>
                  Thêm máy chủ GoClaw Agent để bắt đầu tự động hóa quy trình dựng và xuất bản video.
                </Text>
              </FadeIn>
            ) : null}

            {/* Danh sách Agent Cards */}
            {agents?.length > 0 ? (
              <View style={styles.list}>
                {agents.map((agent, index) => {
                  const isTesting = testingId === agent.id;
                  const testStatus = testResults[agent.id];

                  return (
                    <FadeIn key={agent.id} style={styles.agentCard} delay={stagger(index, 90, 120)} distance={20}>
                      {/* Header của Card */}
                      <View style={styles.cardHeader}>
                        <View style={styles.cardAvatar}>
                          <AgentIcon size={22} color={colors.primary} />
                        </View>
                        <View style={styles.cardTitleBox}>
                          <Text style={styles.cardTitle} numberOfLines={1}>
                            {agent.name}
                          </Text>
                          <View style={styles.domainRow}>
                            <PluginIcon size={13} color={colors.textMuted} />
                            <Text style={styles.domainText} numberOfLines={1}>
                              {agent.domain || 'Chưa có domain'}
                            </Text>
                          </View>
                        </View>

                        {/* Nút Sửa & Xóa */}
                        <View style={styles.cardControls}>
                          <Pressable
                            style={({ pressed }) => [styles.ctrlBtn, pressed && styles.pressed]}
                            onPress={() => handleEditAgent(agent)}
                            accessibilityLabel="Sửa"
                            hitSlop={8}
                          >
                            <PencilIcon size={16} color={colors.textSecondary} />
                          </Pressable>
                          <Pressable
                            style={({ pressed }) => [styles.ctrlBtn, pressed && styles.pressed]}
                            onPress={() => handleDeleteAgent(agent)}
                            accessibilityLabel="Xóa"
                            hitSlop={8}
                          >
                            <TrashIcon size={16} color={colors.error} />
                          </Pressable>
                        </View>
                      </View>

                      {/* Thông tin Key bảo mật */}
                      <View style={styles.keyInfoRow}>
                        <View style={styles.keyBadge}>
                          <Text style={styles.keyBadgeLabel}>API Key:</Text>
                          <Text style={styles.keyBadgeVal}>
                            {agent.has_api_key ? agent.masked_api_key : 'Chưa cấu hình'}
                          </Text>
                        </View>
                        {agent.has_agent_key ? (
                          <View style={styles.keyBadge}>
                            <Text style={styles.keyBadgeLabel}>Agent Key:</Text>
                            <Text style={styles.keyBadgeVal}>{agent.masked_agent_key}</Text>
                          </View>
                        ) : null}
                      </View>

                      {/* Trạng thái Test Kết Nối (Pill thanh lịch, không dùng icon tick to giả tạo) */}
                      {testStatus ? (
                        <FadeIn
                          distance={8}
                          duration={360}
                          style={[
                            styles.statusPill,
                            testStatus.ok ? styles.statusPillOk : styles.statusPillFail,
                          ]}
                        >
                          <Breathing duration={1600} scaleTo={1.5} opacityFrom={1} opacityTo={0.55}>
                            <View
                              style={[
                                styles.statusDot,
                                testStatus.ok ? styles.statusDotOk : styles.statusDotFail,
                              ]}
                            />
                          </Breathing>
                          <Text
                            style={[
                              styles.statusText,
                              testStatus.ok ? styles.statusTextOk : styles.statusTextFail,
                            ]}
                          >
                            {testStatus.message}
                          </Text>
                        </FadeIn>
                      ) : null}

                      {/* Nút Test kết nối của thẻ */}
                      <Pressable
                        style={({ pressed }) => [
                          styles.testCardBtn,
                          pressed && styles.pressed,
                          isTesting && styles.btnDisabled,
                        ]}
                        onPress={() => handleTestAgent(agent)}
                        disabled={isTesting}
                      >
                        {isTesting ? (
                          <ActivityIndicator size="small" color={colors.gold} />
                        ) : (
                          <Text style={styles.testCardBtnText}>Kiểm tra kết nối</Text>
                        )}
                      </Pressable>
                    </FadeIn>
                  );
                })}
              </View>
            ) : null}
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
    paddingTop: 14,
    paddingBottom: 48,
  },
  page: {
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
  },
  topAction: {
    marginBottom: 22,
  },
  formContainer: {
    backgroundColor: colors.card,
    padding: 20,
    borderRadius: 24,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    shadowColor: colors.shadow,
    shadowOpacity: 0.16,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 10 },
    elevation: 4,
  },
  loading: {
    marginVertical: 32,
  },
  error: {
    color: colors.error,
    fontSize: 13.5,
    textAlign: 'center',
    marginBottom: 16,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.errorBorder,
    backgroundColor: colors.errorSoft,
    overflow: 'hidden',
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 44,
    paddingHorizontal: 24,
    borderRadius: 24,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    backgroundColor: colors.card,
  },
  emptyIconBox: {
    width: 68,
    height: 68,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 18,
  },
  emptyTitle: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 21,
    fontWeight: '600',
  },
  emptyOrnament: {
    marginTop: 12,
    marginBottom: 12,
  },
  emptySubtitle: {
    color: colors.textSecondary,
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 21,
    maxWidth: 320,
  },
  list: {
    gap: 14,
  },
  agentCard: {
    backgroundColor: colors.card,
    borderRadius: 22,
    padding: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    shadowColor: colors.shadow,
    shadowOpacity: 0.12,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 2,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  cardAvatar: {
    width: 46,
    height: 46,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 14,
  },
  cardTitleBox: {
    flex: 1,
    gap: 4,
  },
  cardTitle: {
    color: colors.text,
    fontSize: 16.5,
    fontWeight: '700',
    letterSpacing: 0.1,
  },
  domainRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  domainText: {
    flexShrink: 1,
    color: colors.textMuted,
    fontSize: 12.5,
  },
  cardControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  ctrlBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: {
    opacity: 0.7,
  },
  keyInfoRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 16,
    paddingTop: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderStrong,
  },
  keyBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 8,
  },
  keyBadgeLabel: {
    color: colors.textMuted,
    fontSize: 10.5,
    fontWeight: '700',
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },
  keyBadgeVal: {
    color: colors.textSecondary,
    fontSize: 11.5,
    fontFamily: fonts.mono,
  },
  testCardBtn: {
    height: 42,
    borderRadius: 12,
    backgroundColor: colors.goldSoft,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 14,
  },
  testCardBtnText: {
    color: colors.gold,
    fontSize: 13.5,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  /* Modern Status Pill */
  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 9,
    paddingHorizontal: 12,
    borderRadius: 12,
    marginTop: 12,
    borderWidth: 1,
  },
  statusPillOk: {
    backgroundColor: colors.successSoft,
    borderColor: colors.successBorder,
  },
  statusPillFail: {
    backgroundColor: colors.errorSoft,
    borderColor: colors.errorBorder,
  },
  statusDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
  },
  statusDotOk: {
    backgroundColor: colors.success,
  },
  statusDotFail: {
    backgroundColor: colors.error,
  },
  statusText: {
    flexShrink: 1,
    fontSize: 12.5,
    fontWeight: '600',
  },
  statusTextOk: {
    color: colors.success,
  },
  statusTextFail: {
    color: colors.error,
  },
});
