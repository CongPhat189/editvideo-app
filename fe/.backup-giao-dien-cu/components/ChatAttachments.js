import { useVideoPlayer, VideoView } from 'expo-video';
import { useState } from 'react';
import { Image, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { CloseIcon, PlayIcon } from '@/components/HomeIcons';
import { useThemeStyles } from '@/constants/theme';
import { isImage, isVideo } from '@/services/attachments';

const VideoModal = ({ url, onClose }) => {
  const styles = useThemeStyles(createStyles);

  const insets = useSafeAreaInsets();
  const player = useVideoPlayer(url, (videoPlayer) => videoPlayer.play());

  return (
    <Modal visible animationType="fade" onRequestClose={onClose}>
      <View style={[styles.videoPage, { paddingTop: insets.top + 8, paddingBottom: insets.bottom + 8 }]}>
        <Pressable
          onPress={onClose}
          style={({ pressed }) => [styles.videoClose, pressed && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel="Đóng video"
        >
          <CloseIcon />
        </Pressable>
        <VideoView style={styles.video} player={player} nativeControls contentFit="contain" />
      </View>
    </Modal>
  );
};

const VideoTile = ({ style, size = 28 }) => {
  const styles = useThemeStyles(createStyles);
  return (
    <View style={[styles.videoTile, style]}>
      <PlayIcon size={size} />
    </View>
  );
};

export const MessageAttachments = ({ attachments, align = 'flex-start' }) => {
  const styles = useThemeStyles(createStyles);

  const [playingUrl, setPlayingUrl] = useState(null);

  return (
    <View style={[styles.list, { alignItems: align }]}>
      {attachments.map((file) => {
        if (isImage(file.mime_type) && file.url) {
          return (
            <Image
              key={file.id}
              source={{ uri: file.url }}
              style={styles.media}
              accessibilityLabel={file.file_name}
            />
          );
        }
        if (isVideo(file.mime_type) && file.url) {
          return (
            <Pressable
              key={file.id}
              onPress={() => setPlayingUrl(file.url)}
              style={({ pressed }) => pressed && styles.pressed}
              accessibilityRole="button"
              accessibilityLabel={`Xem video ${file.file_name}`}
            >
              <VideoTile style={styles.media} />
            </Pressable>
          );
        }
        return (
          <View key={file.id} style={styles.fileRow}>
            <Text style={styles.fileName} numberOfLines={1}>{file.file_name}</Text>
          </View>
        );
      })}
      {playingUrl ? <VideoModal url={playingUrl} onClose={() => setPlayingUrl(null)} /> : null}
    </View>
  );
};

export const PendingAttachments = ({ files, onRemove }) => {
  const styles = useThemeStyles(createStyles);
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.pending}
      keyboardShouldPersistTaps="handled"
    >
      {files.map((file) => (
        <View key={file.uri} style={styles.thumb}>
          {isVideo(file.mimeType) ? (
            <VideoTile style={styles.thumbMedia} size={22} />
          ) : (
            <Image source={{ uri: file.uri }} style={styles.thumbMedia} accessibilityLabel={file.fileName} />
          )}
          <Pressable
            onPress={() => onRemove(file.uri)}
            hitSlop={10}
            style={({ pressed }) => [styles.remove, pressed && styles.pressed]}
            accessibilityRole="button"
            accessibilityLabel={`Bỏ ${file.fileName}`}
          >
            <CloseIcon size={14} />
          </Pressable>
        </View>
      ))}
    </ScrollView>
  );
};

const createStyles = (colors) => StyleSheet.create({
  pressed: {
    opacity: 0.7,
  },
  list: {
    gap: 8,
  },
  media: {
    width: 220,
    height: 220,
    borderRadius: 16,
    backgroundColor: colors.surface,
  },
  videoTile: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surface,
  },
  fileRow: {
    maxWidth: 260,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 14,
    backgroundColor: colors.surface,
  },
  fileName: {
    color: colors.text,
    fontSize: 14,
  },
  pending: {
    gap: 8,
    paddingHorizontal: 16,
    paddingTop: 10,
  },
  thumb: {
    width: 68,
    height: 68,
  },
  thumbMedia: {
    width: 64,
    height: 64,
    marginTop: 4,
    borderRadius: 12,
    backgroundColor: colors.surface,
  },
  remove: {
    position: 'absolute',
    top: 0,
    right: 0,
    width: 22,
    height: 22,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 11,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.divider,
    backgroundColor: colors.background,
  },
  videoPage: {
    flex: 1,
    backgroundColor: colors.backgroundDeep,
  },
  videoClose: {
    alignSelf: 'flex-end',
    width: 44,
    height: 44,
    marginRight: 16,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 22,
    backgroundColor: colors.surface,
  },
  video: {
    flex: 1,
  },
});
