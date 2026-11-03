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

import { MessageAttachments, PendingAttachments } from '@/components/ChatAttachments';
import DrawerScreen from '@/components/DrawerScreen';
import { CalendarIcon, PlusIcon, SendIcon } from '@/components/HomeIcons';
import PageHeader from '@/components/PageHeader';
import { MyUserContext } from '@/config/Contexts';
import { colors } from '@/constants/theme';
import { MAX_FILES, pickMedia } from '@/services/attachments';
import { getErrorMessage } from '@/services/auth';
import {
  getMessages,
  getProject,
  markProjectOpened,
  sendMessage,
  sendMessageWithFiles,
} from '@/services/projects';

const POLL_INTERVAL = 3000;
const MAX_MESSAGE_LENGTH = 20000;
const IN_PROGRESS = ['pending', 'processing'];

const MessageBubble = ({ message }) => {
  const attachments = message.attachments ?? [];
  if (message.role === 'user') {
    return (
      <View style={styles.userMessage}>
        {attachments.length > 0 ? <MessageAttachments attachments={attachments} align="flex-end" /> : null}
        {message.content ? (
          <View style={styles.userBubble}>
            <Text style={styles.messageText} selectable>{message.content}</Text>
          </View>
        ) : null}
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
  return (
    <View style={styles.replyMessage}>
      {attachments.length > 0 ? <MessageAttachments attachments={attachments} /> : null}
      {message.content ? <Text style={styles.messageText} selectable>{message.content}</Text> : null}
    </View>
  );
};

export default function ProjectChat() {
  const { id } = useLocalSearchParams();

  return (
    <DrawerScreen>
      {(menuButton) => <ChatContent id={id} menuButton={menuButton} />}
    </DrawerScreen>
  );
}

function ChatContent({ id, menuButton }) {
  const [user] = use(MyUserContext);
  const token = user?.access_token;
  const [project, setProject] = useState(null);
  const [messages, setMessages] = useState([]);
  const [nextBefore, setNextBefore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [text, setText] = useState('');
  const [files, setFiles] = useState([]);
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

  const handlePickFiles = async () => {
    const remaining = MAX_FILES - files.length;
    if (remaining <= 0) {
      setSendError(`Mỗi tin gửi tối đa ${MAX_FILES} file`);
      return;
    }
    setSendError('');
    try {
      const picked = await pickMedia(remaining);
      setFiles((current) => {
        const newFiles = picked.files.filter((file) => !current.some((item) => item.uri === file.uri));
        return [...current, ...newFiles];
      });
      if (picked.error) setSendError(picked.error);
    } catch {
      setSendError('Không mở được thư viện ảnh');
    }
  };

  const handleSend = async () => {
    const content = text.trim();
    if ((!content && files.length === 0) || sending) return;

    const sentFiles = files;
    const localUserMessage = {
      id: 'local-user',
      role: 'user',
      content,
      status: 'completed',
      attachments: sentFiles.map((file) => ({
        id: file.uri,
        file_name: file.fileName,
        mime_type: file.mimeType,
        url: file.uri,
      })),
    };
    const localReply = { id: 'local-reply', role: 'assistant', status: 'processing' };
    setMessages((current) => [localReply, localUserMessage, ...current]);
    setText('');
    setFiles([]);
    setSendError('');
    setSending(true);
    try {
      const result = sentFiles.length > 0
        ? await sendMessageWithFiles(token, id, content, sentFiles)
        : await sendMessage(token, id, content);
      setMessages((current) => [
        ...(result.assistant_message ? [result.assistant_message] : []),
        result.user_message,
        ...current.filter((message) => !message.id.startsWith('local-')),
      ]);
    } catch (error) {
      setMessages((current) => current.filter((message) => !message.id.startsWith('local-')));
      setText(content);
      setFiles(sentFiles);
      setSendError(getErrorMessage(error));
    } finally {
      setSending(false);
    }
  };

  const canSend = (text.trim().length > 0 || files.length > 0) && !sending;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />
      <PageHeader title={project?.title || ''} left={menuButton} />
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
        {files.length > 0 ? (
          <View>
            <PendingAttachments
              files={files}
              onRemove={(uri) => setFiles((current) => current.filter((file) => file.uri !== uri))}
            />
          </View>
        ) : null}
        <View style={styles.composer}>
          <Pressable
            onPress={handlePickFiles}
            style={({ pressed }) => [styles.scheduleButton, pressed && styles.pressed]}
            accessibilityRole="button"
            accessibilityLabel="Thêm ảnh hoặc video"
          >
            <PlusIcon size={22} />
          </Pressable>
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
  userMessage: {
    alignItems: 'flex-end',
    gap: 8,
  },
  replyMessage: {
    alignItems: 'flex-start',
    gap: 8,
  },
  userBubble: {
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
