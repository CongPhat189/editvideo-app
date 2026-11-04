import { use, useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import AuthButton from '@/components/AuthButton';
import AuthField from '@/components/AuthField';
import { LockIcon } from '@/components/AuthIcons';
import { AgentIcon, PluginIcon } from '@/components/HomeIcons';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import { createAgent, testAgentConnection } from '@/services/agents';
import { getErrorMessage } from '@/services/auth';

const MAX_NAME_LENGTH = 150;
const MAX_DOMAIN_LENGTH = 255;
const DOMAIN_FORMAT = /^https?:\/\/[^\s/]+\.?[^\s]*$/i;

export default function AgentForm({ onSaved }) {
  const [user] = use(MyUserContext);
  const [name, setName] = useState('');
  const [domain, setDomain] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [agentKey, setAgentKey] = useState('');
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [connected, setConnected] = useState(null);
  const domainRef = useRef(null);
  const apiKeyRef = useRef(null);
  const agentKeyRef = useRef(null);

  const busy = saving || testing;

  // Chỉ nút Lưu cần Name, nút Kiểm tra chỉ dùng Domain và 2 key
  const validate = (needName) => {
    const trimmedDomain = domain.trim();
    const nextErrors = {};
    if (needName && !name.trim()) nextErrors.name = 'Vui lòng nhập Name';
    if (!trimmedDomain) nextErrors.domain = 'Vui lòng nhập Domain';
    else if (!DOMAIN_FORMAT.test(trimmedDomain)) nextErrors.domain = 'Domain phải bắt đầu bằng http:// hoặc https://';
    if (!apiKey.trim()) nextErrors.apiKey = 'Vui lòng nhập API Key';
    if (!agentKey.trim()) nextErrors.agentKey = 'Vui lòng nhập Agent Key';
    setErrors(nextErrors);
    setFormError('');
    setConnected(null);
    return Object.keys(nextErrors).length === 0;
  };

  const getKeys = () => ({ domain: domain.trim(), apiKey: apiKey.trim(), agentKey: agentKey.trim() });

  const handleTest = async () => {
    if (busy || !validate(false)) return;
    setTesting(true);
    try {
      const connection = await testAgentConnection(user.access_token, getKeys());
      setConnected(connection.ok);
    } catch (error) {
      setFormError(getErrorMessage(error));
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (busy || !validate(true)) return;
    setSaving(true);
    try {
      await createAgent(user.access_token, { name: name.trim(), ...getKeys() });
      onSaved();
    } catch (error) {
      setFormError(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  // Sửa thông tin thì kết quả kiểm tra cũ không còn đúng
  const editConnection = (setValue) => (value) => {
    setValue(value);
    setConnected(null);
  };

  return (
    <View>
      <AuthField
        label="Name"
        icon={<AgentIcon size={20} color={colors.textMuted} />}
        error={errors.name}
        value={name}
        onChangeText={setName}
        placeholder="Tên Agent"
        maxLength={MAX_NAME_LENGTH}
        returnKeyType="next"
        onSubmitEditing={() => domainRef.current?.focus()}
      />
      <AuthField
        ref={domainRef}
        label="Domain"
        icon={<PluginIcon size={20} color={colors.textMuted} />}
        error={errors.domain}
        value={domain}
        onChangeText={editConnection(setDomain)}
        placeholder="https://goclaw.example.com"
        maxLength={MAX_DOMAIN_LENGTH}
        keyboardType="url"
        autoCapitalize="none"
        autoCorrect={false}
        returnKeyType="next"
        onSubmitEditing={() => apiKeyRef.current?.focus()}
      />
      <AuthField
        ref={apiKeyRef}
        label="API Key"
        icon={<LockIcon />}
        error={errors.apiKey}
        value={apiKey}
        onChangeText={editConnection(setApiKey)}
        placeholder="••••••••"
        secureTextEntry
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="off"
        returnKeyType="next"
        onSubmitEditing={() => agentKeyRef.current?.focus()}
      />
      <AuthField
        ref={agentKeyRef}
        label="Agent Key"
        icon={<LockIcon />}
        error={errors.agentKey}
        value={agentKey}
        onChangeText={editConnection(setAgentKey)}
        placeholder="••••••••"
        secureTextEntry
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="off"
        returnKeyType="done"
        onSubmitEditing={handleSave}
      />

      {formError ? <Text style={styles.formError}>{formError}</Text> : null}
      {connected === true ? <Text style={styles.connected}>Agent kết nối thành công</Text> : null}
      {connected === false ? <Text style={styles.formError}>Agent không kết nối được</Text> : null}
      <View style={styles.actions}>
        <AuthButton title="Kiểm tra kết nối" variant="secondary" onPress={handleTest} loading={testing} />
        <AuthButton title="Lưu Agent" onPress={handleSave} loading={saving} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  actions: {
    gap: 12,
  },
  connected: {
    color: colors.success,
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 12,
  },
  formError: {
    color: colors.error,
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 12,
  },
});
