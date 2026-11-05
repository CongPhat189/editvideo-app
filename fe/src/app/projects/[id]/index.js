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
import { AgentIcon, CalendarIcon, MicIcon, PlusIcon, SendIcon } from '@/components/HomeIcons';
import { AmbientGlow, BrandMark, GoldGradient } from '@/components/Luxe';
import { Breathing, FadeIn, PopIn, Shimmer, TypingDots } from '@/components/Motion';
import PageHeader from '@/components/PageHeader';
import { MyUserContext } from '@/config/Contexts';
import { fonts, useThemeColors, useThemeStyles } from '@/constants/theme';
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

const MessageBubble = (props) => (
  // Danh sách đảo ngược (inverted) nên dùng khoảng cách âm để tin nhắn trồi lên từ dưới
  <FadeIn distance={props.message.role === 'user' ? -10 : -14} duration={420}>
    <MessageContent {...props} />
  </FadeIn>
);

const MessageContent = ({ message, showScheduleButton, onLongPress, onSchedule }) => {
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

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
        <BrandMark size={24} />
        <View style={styles.pendingPill}>
          <TypingDots />
          <Text style={styles.pendingText}>Agent đang trả lời</Text>
        </View>
      </View>
    );
  }
  if (message.status === 'failed') {
    return (
      <View style={styles.failedBox}>
        <Text style={styles.failedText}>{message.error_message || 'Agent không trả lời được'}</Text>
      </View>
    );
  }
  const canSchedule = Boolean(message.content?.trim() || attachments.length > 0);
  return (
    <View style={styles.replyMessage}>
      <View style={styles.replyHeader}>
        <BrandMark size={24} />
        <Text style={styles.replyAuthor}>Agent</Text>
      </View>
      <Pressable
        style={styles.replyBody}
        onLongPress={onLongPress}
        delayLongPress={350}
        disabled={message.status !== 'completed' || !canSchedule}
        accessibilityRole="button"
        accessibilityLabel="Nhấn giữ để đặt lịch tin nhắn này"
      >
        {attachments.length > 0 ? <MessageAttachments attachments={attachments} /> : null}
        {message.content ? <Text style={styles.messageText}>{message.content}</Text> : null}
      </Pressable>
      {showScheduleButton ? (
        <PopIn from={0.8}>
        <Pressable
          onPress={onSchedule}
          style={({ pressed }) => [styles.scheduleMessageButton, pressed && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel="Đặt lịch nội dung này"
        >
          <CalendarIcon size={15} color={colors.gold} />
          <Text style={styles.scheduleMessageButtonText}>Đặt lịch</Text>
        </Pressable>
        </PopIn>
      ) : null}
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
  const colors = useThemeColors();
  const styles = useThemeStyles(createStyles);

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
  const [scheduleActionMessageId, setScheduleActionMessageId] = useState(null);
  const loadingOlder = useRef(false);
  const inputRef = useRef(null);

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
      <StatusBar style={colors.statusBar} />
      <AmbientGlow height={260} intensity={0.6} />
      <PageHeader title={project?.title || ''} left={menuButton} />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.gold} />
          </View>
        ) : null}
        {!loading && loadError ? (
          <View style={styles.center}>
            <Text style={styles.failedText}>{loadError}</Text>
          </View>
        ) : null}
        {!loading && !loadError && messages.length === 0 ? (
          <View style={styles.center}>
            <FadeIn style={styles.emptyState} distance={18}>
              <Breathing style={styles.emptyIcon} duration={3200} scaleTo={1.06}>
                <GoldGradient />
                <Shimmer interval={2400} />
                <View><AgentIcon size={26} color={colors.onPrimary} /></View>
              </Breathing>
              <Text style={styles.emptyTitle}>Bắt đầu cuộc trò chuyện</Text>
              <Text style={styles.emptyText}>Mô tả video bạn muốn tạo. Bạn cũng có thể gửi ảnh hoặc video để Agent tham khảo.</Text>
            </FadeIn>
          </View>
        ) : null}
        {!loading && !loadError && messages.length > 0 ? (
          <FlatList
            style={styles.flex}
            inverted
            data={messages}
            keyExtractor={(message) => message.id}
            renderItem={({ item }) => (
              <MessageBubble
                message={item}
                showScheduleButton={String(scheduleActionMessageId) === String(item.id)}
                onLongPress={() => setScheduleActionMessageId(item.id)}
                onSchedule={() => router.push({
                  pathname: '/projects/[id]/schedule',
                  params: { id, contentMessageId: item.id },
                })}
              />
            )}
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
        <View style={styles.composerWrap}>
          <View style={styles.composer}>
            <TextInput
              ref={inputRef}
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
            <View style={styles.composerToolbar}>
              <View style={styles.composerActions}>
                <Pressable
                  onPress={handlePickFiles}
                  style={({ pressed }) => [styles.actionButton, pressed && styles.pressed]}
                  accessibilityRole="button"
                  accessibilityLabel="Thêm ảnh hoặc video"
                >
                  <PlusIcon size={19} color={colors.textSecondary} />
                </Pressable>
                <Pressable
                  onPress={() => inputRef.current?.focus()}
                  disabled={sending}
                  style={({ pressed }) => [styles.actionButton, pressed && styles.pressed]}
                  accessibilityRole="button"
                  accessibilityLabel="Mở bàn phím để nhập bằng giọng nói"
                  accessibilityState={{ disabled: sending }}
                >
                  <MicIcon size={19} color={colors.textSecondary} />
                </Pressable>
              </View>
              <Pressable
                onPress={handleSend}
                disabled={!canSend}
                style={({ pressed }) => [styles.sendButton, !canSend && styles.sendButtonDisabled, pressed && styles.pressed]}
                accessibilityRole="button"
                accessibilityLabel="Gửi"
                accessibilityState={{ disabled: !canSend }}
              >
                {canSend ? <GoldGradient /> : null}
                <PopIn key={canSend ? 'ready' : 'idle'} from={canSend ? 0.5 : 0.85}>
                  <SendIcon size={20} color={canSend ? colors.onPrimary : colors.textMuted} />
                </PopIn>
              </Pressable>
            </View>
          </View>
          <Text style={styles.composerHint}>AI có thể mắc lỗi. Hãy kiểm tra lại thông tin quan trọng.</Text>
        </View>
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
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  emptyState: {
    alignItems: 'center',
    maxWidth: 340,
  },
  emptyIcon: {
    width: 64,
    height: 64,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 20,
    overflow: 'hidden',
    marginBottom: 20,
  },
  emptyTitle: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 22,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 10,
  },
  emptyText: {
    color: colors.textSecondary,
    fontSize: 14.5,
    lineHeight: 22,
    textAlign: 'center',
  },
  messages: {
    gap: 18,
    paddingHorizontal: 16,
    paddingVertical: 16,
  },
  userMessage: {
    alignItems: 'flex-end',
    gap: 8,
  },
  replyMessage: {
    alignItems: 'flex-start',
    gap: 10,
  },
  replyHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  replyAuthor: {
    color: colors.gold,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  replyBody: {
    alignSelf: 'stretch',
    gap: 8,
    paddingLeft: 32,
  },
  scheduleMessageButton: {
    minHeight: 36,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    marginLeft: 32,
    paddingHorizontal: 14,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
  },
  scheduleMessageButtonText: {
    color: colors.gold,
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  userBubble: {
    maxWidth: '85%',
    paddingHorizontal: 16,
    paddingVertical: 11,
    borderRadius: 20,
    borderBottomRightRadius: 6,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSoft,
  },
  messageText: {
    color: colors.text,
    fontSize: 16,
    lineHeight: 25,
  },
  replyPending: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  pendingPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
  },
  pendingText: {
    color: colors.textSecondary,
    fontSize: 13.5,
    fontStyle: 'italic',
  },
  failedBox: {
    alignSelf: 'flex-start',
    maxWidth: '90%',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.errorBorder,
    backgroundColor: colors.errorSoft,
  },
  failedText: {
    color: colors.error,
    fontSize: 14,
    lineHeight: 20,
    textAlign: 'center',
  },
  sendError: {
    color: colors.error,
    fontSize: 13.5,
    textAlign: 'center',
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  composer: {
    paddingHorizontal: 12,
    paddingTop: 6,
    paddingBottom: 10,
    borderRadius: 28,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
    shadowColor: colors.shadow,
    shadowOpacity: 0.22,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  composerWrap: {
    paddingHorizontal: 12,
    paddingTop: 6,
    paddingBottom: 2,
  },
  composerToolbar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  composerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  actionButton: {
    width: 38,
    height: 38,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 19,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surfaceRaised,
  },
  scheduleAction: {
    height: 36,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 11,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.divider,
  },
  scheduleLabel: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: '500',
  },
  composerHint: {
    color: colors.textMuted,
    fontSize: 11,
    letterSpacing: 0.2,
    textAlign: 'center',
    paddingTop: 8,
    paddingBottom: 4,
  },
  input: {
    width: '100%',
    minHeight: 44,
    maxHeight: 140,
    paddingHorizontal: 6,
    paddingTop: 10,
    paddingBottom: 10,
    color: colors.text,
    fontSize: 16,
    textAlignVertical: 'top',
    outlineStyle: 'none',
  },
  sendButton: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 20,
    overflow: 'hidden',
    backgroundColor: colors.primary,
  },
  sendButtonDisabled: {
    backgroundColor: colors.surfaceRaised,
  },
  pressed: {
    opacity: 0.75,
  },
});
