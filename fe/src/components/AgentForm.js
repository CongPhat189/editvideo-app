import { useEffect, use, useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import AuthButton from '@/components/AuthButton';
import AuthField from '@/components/AuthField';
import { LockIcon } from '@/components/AuthIcons';
import { AgentIcon, PluginIcon } from '@/components/HomeIcons';
import { Eyebrow } from '@/components/Luxe';
import { FadeIn } from '@/components/Motion';
import { MyUserContext } from '@/config/Contexts';
import { fonts, useThemeColors, useThemeStyles } from '@/constants/theme';
import {
  createAgent,
  getAgentErrorMessage,
  testAgentConnection,
  testSavedAgentConnection,
  updateAgent,
} from '@/services/agents';

const MAX_NAME_LENGTH = 150;
const MAX_DOMAIN_LENGTH = 255;
const DOMAIN_FORMAT = /^https?:\/\/[^\s/]+\.?[^\s]*$/i;

export default function AgentForm({ onSaved, agent = null, onCancel }) {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

  const [user] = use(MyUserContext);
  const isEditing = !!agent;

  const [name, setName] = useState(agent?.name || '');
  const [domain, setDomain] = useState(agent?.domain || '');
  const [apiKey, setApiKey] = useState('');
  const [agentKey, setAgentKey] = useState('');
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState(null); // { ok: bool, message: str }

  const domainRef = useRef(null);
  const apiKeyRef = useRef(null);
  const agentKeyRef = useRef(null);

  useEffect(() => {
    if (agent) {
      setName(agent.name || '');
      setDomain(agent.domain || '');
      setApiKey('');
      setAgentKey('');
    } else {
      setName('');
      setDomain('');
      setApiKey('');
      setAgentKey('');
    }
    setErrors({});
    setFormError('');
    setConnectionStatus(null);
  }, [agent]);

  const busy = saving || testing;

  const validate = (needName = true) => {
    const trimmedDomain = domain.trim();
    const nextErrors = {};

    if (needName && !name.trim()) nextErrors.name = 'Vui lòng nhập Tên Agent';

    if (!trimmedDomain) {
      nextErrors.domain = 'Vui lòng nhập Domain GoClaw';
    } else if (!DOMAIN_FORMAT.test(trimmedDomain)) {
      nextErrors.domain = 'Domain phải bắt đầu bằng http:// hoặc https://';
    }

    // Khi tạo mới thì cần nhập key; khi sửa nếu bỏ trống thì giữ nguyên key cũ
    if (!isEditing) {
      if (!apiKey.trim()) nextErrors.apiKey = 'Vui lòng nhập API Key';
    }

    setErrors(nextErrors);
    setFormError('');
    setConnectionStatus(null);
    return Object.keys(nextErrors).length === 0;
  };

  const handleTest = async () => {
    if (busy || !validate(false)) return;
    setTesting(true);
    setConnectionStatus(null);
    setFormError('');

    try {
      let res;
      // Nếu đang sửa và người dùng không nhập key mới, test bằng thông tin đã lưu
      if (isEditing && !apiKey.trim() && !agentKey.trim() && domain.trim() === agent.domain) {
        res = await testSavedAgentConnection(user.access_token, agent.id);
      } else {
        res = await testAgentConnection(user.access_token, {
          domain: domain.trim(),
          apiKey: apiKey.trim() || undefined,
          agentKey: agentKey.trim() || undefined,
        });
      }

      setConnectionStatus({
        ok: res.ok,
        message: res.ok ? 'Kết nối GoClaw thành công' : (res.message || 'Không kết nối được GoClaw'),
      });
    } catch (error) {
      setConnectionStatus({
        ok: false,
        message: getAgentErrorMessage(error),
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (busy || !validate(true)) return;
    setSaving(true);
    setFormError('');

    try {
      if (isEditing) {
        await updateAgent(user.access_token, agent.id, {
          name: name.trim(),
          domain: domain.trim(),
          apiKey: apiKey.trim() || undefined,
          agentKey: agentKey.trim() || undefined,
        });
      } else {
        await createAgent(user.access_token, {
          name: name.trim(),
          domain: domain.trim(),
          apiKey: apiKey.trim(),
          agentKey: agentKey.trim(),
        });
      }
      onSaved?.();
    } catch (error) {
      setFormError(getAgentErrorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const editField = (setter) => (val) => {
    setter(val);
    setConnectionStatus(null);
    setFormError('');
  };

  return (
    <View style={styles.formCard}>
      {isEditing && (
        <View style={styles.editingHeader}>
          <Eyebrow style={styles.editingEyebrow}>Agent</Eyebrow>
          <Text style={styles.editingTitle}>Chỉnh sửa Agent</Text>
          <Text style={styles.editingSubtitle}>Cập nhật tên, domain hoặc thay đổi khóa bảo mật</Text>
        </View>
      )}

      <AuthField
        label="Tên Agent"
        icon={<AgentIcon size={20} color={colors.textMuted} />}
        error={errors.name}
        value={name}
        onChangeText={editField(setName)}
        placeholder="VD: Trợ lý kịch bản, Video Editor"
        maxLength={MAX_NAME_LENGTH}
        returnKeyType="next"
        onSubmitEditing={() => domainRef.current?.focus()}
      />

      <AuthField
        ref={domainRef}
        label="Domain Máy Chủ"
        icon={<PluginIcon size={20} color={colors.textMuted} />}
        error={errors.domain}
        value={domain}
        onChangeText={editField(setDomain)}
        placeholder="https://goclaw.cua-ban.com"
        maxLength={MAX_DOMAIN_LENGTH}
        keyboardType="url"
        autoCapitalize="none"
        autoCorrect={false}
        returnKeyType="next"
        onSubmitEditing={() => apiKeyRef.current?.focus()}
      />

      <AuthField
        ref={apiKeyRef}
        label={isEditing ? 'API Key mới (bỏ trống nếu giữ nguyên)' : 'API Key'}
        icon={<LockIcon />}
        error={errors.apiKey}
        value={apiKey}
        onChangeText={editField(setApiKey)}
        placeholder={isEditing && agent?.has_api_key ? `Đang dùng: ${agent.masked_api_key}` : '••••••••'}
        secureTextEntry
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="off"
        returnKeyType="next"
        onSubmitEditing={() => agentKeyRef.current?.focus()}
      />

      <AuthField
        ref={agentKeyRef}
        label={isEditing ? 'Agent Key mới (bỏ trống nếu giữ nguyên)' : 'Agent Key'}
        icon={<LockIcon />}
        error={errors.agentKey}
        value={agentKey}
        onChangeText={editField(setAgentKey)}
        placeholder={isEditing && agent?.has_agent_key ? `Đang dùng: ${agent.masked_agent_key}` : '••••••••'}
        secureTextEntry
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="off"
        returnKeyType="done"
        onSubmitEditing={handleSave}
      />

      {formError ? <Text style={styles.formErrorText}>{formError}</Text> : null}

      {/* Modern Status Pill (Không dùng icon tick to giả tạo) */}
      {connectionStatus ? (
        <FadeIn
          distance={8}
          duration={360}
          style={[
            styles.statusPill,
            connectionStatus.ok ? styles.statusPillOk : styles.statusPillFail,
          ]}
        >
          <View
            style={[
              styles.statusDot,
              connectionStatus.ok ? styles.statusDotOk : styles.statusDotFail,
            ]}
          />
          <Text
            style={[
              styles.statusText,
              connectionStatus.ok ? styles.statusTextOk : styles.statusTextFail,
            ]}
          >
            {connectionStatus.message}
          </Text>
        </FadeIn>
      ) : null}

      <View style={styles.actions}>
        <AuthButton
          title="Kiểm tra kết nối"
          variant="secondary"
          onPress={handleTest}
          loading={testing}
        />
        <AuthButton
          title={isEditing ? 'Lưu thay đổi' : 'Lưu Agent'}
          onPress={handleSave}
          loading={saving}
        />
        {onCancel ? (
          <AuthButton
            title="Hủy"
            variant="secondary"
            onPress={onCancel}
            disabled={busy}
          />
        ) : null}
      </View>
    </View>
  );
}

const createStyles = (colors) => StyleSheet.create({
  formCard: {
    paddingVertical: 4,
  },
  editingHeader: {
    marginBottom: 20,
    paddingBottom: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.borderStrong,
  },
  editingEyebrow: {
    marginBottom: 6,
  },
  editingTitle: {
    fontFamily: fonts.display,
    fontSize: 22,
    fontWeight: '600',
    color: colors.text,
  },
  editingSubtitle: {
    fontSize: 13.5,
    lineHeight: 19,
    color: colors.textSecondary,
    marginTop: 4,
  },
  actions: {
    gap: 12,
    marginTop: 8,
  },
  formErrorText: {
    color: colors.error,
    fontSize: 13,
    textAlign: 'center',
    marginBottom: 14,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.errorBorder,
    backgroundColor: colors.errorSoft,
    overflow: 'hidden',
  },
  /* Modern Minimalist Status Pill */
  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 12,
    marginBottom: 14,
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
    fontSize: 13,
    fontWeight: '500',
  },
  statusTextOk: {
    color: colors.success,
  },
  statusTextFail: {
    color: colors.error,
  },
});
