import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { use, useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { CalendarIcon, SendIcon } from '@/components/HomeIcons';
import PageHeader from '@/components/PageHeader';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import { getErrorMessage } from '@/services/auth';
import { getMessages, getProject, markProjectOpened, sendMessage } from '@/services/projects';

const POLL_INTERVAL = 3000;
const MAX_MESSAGE_LENGTH = 20000;
const IN_PROGRESS = ['pending', 'processing'];

const MessageBubble = ({ message }) => {
  if (message.role === 'user') {
    return (
      <View style={styles.userBubble}>
        <Text style={styles.messageText} selectable>{message.content}</Text>
      </View>
    );
  }
  if (IN_PROGRESS.includes(message.status)) {
    return (
      <View style={styles.replyPending}>
        <ActivityIndicator size="small" color={colors.textSecondary} />
        <Text style={styles.pendingText}>Agent đang trả lời…</Text>
      </View>
    );
  }
  if (message.status === 'failed') {
    return <Text style={styles.failedText}>{message.error_message || 'Agent không trả lời được'}</Text>;
  }
  return <Text style={[styles.messageText, styles.replyText]} selectable>{message.content}</Text>;
};

export default function ProjectChat() {
  const { id } = useLocalSearchParams();
  const [user] = use(MyUserContext);
  const token = user?.access_token;
  const [project, setProject] = useState(null);
  const [messages, setMessages] = useState([]);
  const [nextBefore, setNextBefore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState('');
  const loadingOlder = useRef(false);

  const loadMessages = useCallback(async () => {
    const page = await getMessages(token, id);
    setMessages(page.items);
    setNextBefore(page.next_before);
  }, [token, id]);

  // Chỉ đọc dự án đã có và ghi lại lần mở, không tạo dự án mới
  useEffect(() => {
    if (!token) return;
    getProject(token, id)
      .then((item) => {
        setProject(item);
        return markProjectOpened(token, item.id);
      })
      .catch((error) => setLoadError(getErrorMessage(error)));
  }, [token, id]);

  useFocusEffect(
    useCallback(() => {
      if (!token) return;
      loadMessages()
        .catch((error) => setLoadError(getErrorMessage(error)))
        .finally(() => setLoading(false));
    }, [token, loadMessages])
  );

  // Câu trả lời đang chạy trong nền (vd lịch vừa đến giờ): hỏi lại đến khi xong
  const hasReplyInProgress = !sending && messages.some((message) => IN_PROGRESS.includes(message.status));
  useEffect(() => {
    if (!hasReplyInProgress) return undefined;
    const timer = setInterval(() => {
      loadMessages().catch(() => {});
    }, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [hasReplyInProgress, loadMessages]);

  const loadOlder = async () => {
    if (!nextBefore || loadingOlder.current) return;
    loadingOlder.current = true;
    try {
      const page = await getMessages(token, id, nextBefore);
      setMessages((current) => [...current, ...page.items]);
      setNextBefore(page.next_before);
    } catch (error) {
      setSendError(getErrorMessage(error));
    } finally {
      loadingOlder.current = false;
    }
  };

  const handleSend = async () => {
    const content = text.trim();
    if (!content || sending) return;

    const localUserMessage = { id: 'local-user', role: 'user', content, status: 'completed' };
    const localReply = { id: 'local-reply', role: 'assistant', status: 'processing' };
    setMessages((current) => [localReply, localUserMessage, ...current]);
    setText('');
    setSendError('');
    setSending(true);
    try {
      const result = await sendMessage(token, id, content);
      setMessages((current) => [
        ...(result.assistant_message ? [result.assistant_message] : []),
        result.user_message,
        ...current.filter((message) => !message.id.startsWith('local-')),
      ]);
    } catch (error) {
      setMessages((current) => current.filter((message) => !message.id.startsWith('local-')));
      setText(content);
      setSendError(getErrorMessage(error));
    } finally {
      setSending(false);
    }
  };

  const canSend = text.trim().length > 0 && !sending;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />
      <PageHeader title={project?.title || ''} />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.text} />
          </View>
        ) : null}
        {!loading && loadError ? (
          <View style={styles.center}>
            <Text style={styles.failedText}>{loadError}</Text>
          </View>
        ) : null}
        {!loading && !loadError && messages.length === 0 ? (
          <View style={styles.center}>
            <Text style={styles.emptyText}>Hãy gửi tin nhắn đầu tiên cho dự án này</Text>
          </View>
        ) : null}
        {!loading && !loadError && messages.length > 0 ? (
          <FlatList
            style={styles.flex}
            inverted
            data={messages}
            keyExtractor={(message) => message.id}
            renderItem={({ item }) => <MessageBubble message={item} />}
            contentContainerStyle={styles.messages}
            onEndReached={loadOlder}
            onEndReachedThreshold={0.3}
            keyboardShouldPersistTaps="handled"
          />
        ) : null}

        {sendError ? <Text style={styles.sendError}>{sendError}</Text> : null}
        <View style={styles.composer}>
          <Pressable
            onPress={() => router.push(`/projects/${id}/schedule`)}
            style={({ pressed }) => [styles.scheduleButton, pressed && styles.pressed]}
            accessibilityRole="button"
            accessibilityLabel="Đặt lịch"
          >
            <CalendarIcon size={22} />
          </Pressable>
          <TextInput
            style={styles.input}
            value={text}
            onChangeText={setText}
            placeholder="Nhập tin nhắn"
            placeholderTextColor={colors.textMuted}
            selectionColor={colors.primary}
            accessibilityLabel="Nhập tin nhắn"
            maxLength={MAX_MESSAGE_LENGTH}
            multiline
          />
          <Pressable
            onPress={handleSend}
            disabled={!canSend}
            style={({ pressed }) => [
              styles.sendButton,
              !canSend && styles.sendButtonDisabled,
              pressed && styles.pressed,
            ]}
            accessibilityRole="button"
            accessibilityLabel="Gửi"
            accessibilityState={{ disabled: !canSend }}
          >
            <SendIcon size={22} color={canSend ? colors.onPrimary : colors.textMuted} />
          </Pressable>
        </View>
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
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  emptyText: {
    color: colors.textSecondary,
    fontSize: 16,
    textAlign: 'center',
  },
  messages: {
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  userBubble: {
    alignSelf: 'flex-end',
    maxWidth: '85%',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 18,
    backgroundColor: colors.surface,
  },
  messageText: {
    color: colors.text,
    fontSize: 16,
    lineHeight: 24,
  },
  replyText: {
    alignSelf: 'flex-start',
  },
  replyPending: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  pendingText: {
    color: colors.textSecondary,
    fontSize: 14,
  },
  failedText: {
    color: colors.error,
    fontSize: 14,
    lineHeight: 20,
    textAlign: 'center',
  },
  sendError: {
    color: colors.error,
    fontSize: 14,
    textAlign: 'center',
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  scheduleButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 22,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.divider,
    backgroundColor: colors.surface,
  },
  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 120,
    paddingHorizontal: 16,
    paddingTop: 11,
    paddingBottom: 11,
    borderRadius: 22,
    color: colors.text,
    fontSize: 16,
    backgroundColor: colors.surface,
  },
  sendButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 22,
    backgroundColor: colors.primary,
  },
  sendButtonDisabled: {
    backgroundColor: colors.surface,
  },
  pressed: {
    opacity: 0.7,
  },
});
