import { use, useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import AuthButton from '@/components/AuthButton';
import AuthField from '@/components/AuthField';
import { LockIcon } from '@/components/AuthIcons';
import { AgentIcon, PluginIcon } from '@/components/HomeIcons';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import { createAgent } from '@/services/agents';
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
  const domainRef = useRef(null);
  const apiKeyRef = useRef(null);
  const agentKeyRef = useRef(null);

  const handleSave = async () => {
    const trimmedDomain = domain.trim();
    const nextErrors = {};
    if (!name.trim()) nextErrors.name = 'Vui lòng nhập Name';
    if (!trimmedDomain) nextErrors.domain = 'Vui lòng nhập Domain';
    else if (!DOMAIN_FORMAT.test(trimmedDomain)) nextErrors.domain = 'Domain phải bắt đầu bằng http:// hoặc https://';
    if (!apiKey.trim()) nextErrors.apiKey = 'Vui lòng nhập API Key';
    if (!agentKey.trim()) nextErrors.agentKey = 'Vui lòng nhập Agent Key';
    setErrors(nextErrors);
    setFormError('');
    if (Object.keys(nextErrors).length > 0) return;

    setSaving(true);
    try {
      await createAgent(user.access_token, {
        name: name.trim(),
        domain: trimmedDomain,
        apiKey: apiKey.trim(),
        agentKey: agentKey.trim(),
      });
      onSaved();
    } catch (error) {
      setFormError(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
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
        onChangeText={setDomain}
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
        onChangeText={setApiKey}
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
        onChangeText={setAgentKey}
        placeholder="••••••••"
        secureTextEntry
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="off"
        returnKeyType="done"
        onSubmitEditing={handleSave}
      />

      {formError ? <Text style={styles.formError}>{formError}</Text> : null}
      <AuthButton title="Lưu Agent" onPress={handleSave} loading={saving} />
    </View>
  );
}

const styles = StyleSheet.create({
  formError: {
    color: colors.error,
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 12,
  },
});
