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
import PageHeader from '@/components/PageHeader';
import { MyUserContext } from '@/config/Contexts';
import { useThemeColors, useThemeStyles } from '@/constants/theme';
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
      <StatusBar style={colors.backgroundDeep === '#000000' ? 'light' : 'dark'} />
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
              tintColor={colors.text}
              colors={[colors.text]}
            />
          }
        >
          <View style={styles.page}>
            {error ? <Text style={styles.error}>{error}</Text> : null}

            {agents === null && !error ? (
              <ActivityIndicator color={colors.text} style={styles.loading} />
            ) : null}

            {/* Form Thêm mới / Chỉnh sửa */}
            {formOpen ? (
              <View style={styles.formContainer}>
                <AgentForm
                  agent={editingAgent}
                  onSaved={handleSaved}
                  onCancel={handleCancelForm}
                />
              </View>
            ) : (
              <View style={styles.topAction}>
                <AuthButton title="+ Thêm Agent" onPress={toggleForm} />
              </View>
            )}

            {/* Trạng thái trống */}
            {agents?.length === 0 && !formOpen ? (
              <View style={styles.emptyContainer}>
                <View style={styles.emptyIconBox}>
                  <AgentIcon size={36} color={colors.textMuted} />
                </View>
                <Text style={styles.emptyTitle}>Chưa có Agent nào</Text>
                <Text style={styles.emptySubtitle}>
                  Thêm máy chủ GoClaw Agent để bắt đầu tự động hóa quy trình dựng và xuất bản video.
                </Text>
              </View>
            ) : null}

            {/* Danh sách Agent Cards */}
            {agents?.length > 0 ? (
              <View style={styles.list}>
                {agents.map((agent) => {
                  const isTesting = testingId === agent.id;
                  const testStatus = testResults[agent.id];

                  return (
                    <View key={agent.id} style={styles.agentCard}>
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
                            <PencilIcon size={17} color={colors.textSecondary} />
                          </Pressable>
                          <Pressable
                            style={({ pressed }) => [styles.ctrlBtn, pressed && styles.pressed]}
                            onPress={() => handleDeleteAgent(agent)}
                            accessibilityLabel="Xóa"
                            hitSlop={8}
                          >
                            <TrashIcon size={17} color={colors.error} />
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
                        <View
                          style={[
                            styles.statusPill,
                            testStatus.ok ? styles.statusPillOk : styles.statusPillFail,
                          ]}
                        >
                          <View
                            style={[
                              styles.statusDot,
                              testStatus.ok ? styles.statusDotOk : styles.statusDotFail,
                            ]}
                          />
                          <Text
                            style={[
                              styles.statusText,
                              testStatus.ok ? styles.statusTextOk : styles.statusTextFail,
                            ]}
                          >
                            {testStatus.message}
                          </Text>
                        </View>
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
                          <ActivityIndicator size="small" color={colors.text} />
                        ) : (
                          <Text style={styles.testCardBtnText}>Kiểm tra kết nối</Text>
                        )}
                      </Pressable>
                    </View>
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
    paddingTop: 12,
    paddingBottom: 48,
  },
  page: {
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
  },
  topAction: {
    marginBottom: 20,
  },
  formContainer: {
    backgroundColor: colors.surface,
    padding: 18,
    borderRadius: 20,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: colors.divider,
  },
  loading: {
    marginVertical: 32,
  },
  error: {
    color: colors.error,
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 16,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 48,
    paddingHorizontal: 24,
  },
  emptyIconBox: {
    width: 64,
    height: 64,
    borderRadius: 20,
    backgroundColor: colors.surfaceRaised,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  emptyTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 6,
  },
  emptySubtitle: {
    color: colors.textSecondary,
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 19,
  },
  list: {
    gap: 14,
  },
  agentCard: {
    backgroundColor: colors.surface,
    borderRadius: 18,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.divider,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  cardAvatar: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: colors.surfaceRaised,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  cardTitleBox: {
    flex: 1,
    gap: 2,
  },
  cardTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '600',
  },
  domainRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  domainText: {
    color: colors.textMuted,
    fontSize: 12,
  },
  cardControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  ctrlBtn: {
    width: 32,
    height: 32,
    borderRadius: 8,
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
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
  },
  keyBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: colors.surfaceRaised,
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
  },
  keyBadgeLabel: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: '500',
  },
  keyBadgeVal: {
    color: colors.textSecondary,
    fontSize: 11,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  testCardBtn: {
    height: 36,
    borderRadius: 10,
    backgroundColor: colors.surfaceRaised,
    borderWidth: 1,
    borderColor: colors.divider,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 12,
  },
  testCardBtnText: {
    color: colors.text,
    fontSize: 13,
    fontWeight: '500',
  },
  btnDisabled: {
    opacity: 0.6,
  },
  /* Modern Status Pill */
  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 10,
    marginTop: 10,
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
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  statusDotOk: {
    backgroundColor: colors.success,
  },
  statusDotFail: {
    backgroundColor: colors.error,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '500',
  },
  statusTextOk: {
    color: colors.success,
  },
  statusTextFail: {
    color: colors.error,
  },
});
