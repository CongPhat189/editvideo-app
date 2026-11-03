import * as ImagePicker from 'expo-image-picker';

// Cùng giới hạn với backend (app/services/attachment_service.py)
export const MAX_FILES = 5;
const MAX_FILE_BYTES = 50 * 1024 * 1024;

export const isImage = (mimeType) => mimeType?.startsWith('image/');
export const isVideo = (mimeType) => mimeType?.startsWith('video/');

const toFile = (asset, index) => {
  const mimeType = asset.mimeType ?? (asset.type === 'video' ? 'video/mp4' : 'image/jpeg');
  const extension = mimeType.split('/')[1];
  return {
    uri: asset.uri,
    mimeType,
    fileName: asset.fileName ?? `file-${Date.now()}-${index}.${extension}`,
    fileSize: asset.fileSize,
  };
};

export const pickMedia = async (remaining) => {
  const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!permission.granted) {
    return { files: [], error: 'Hãy cho phép app truy cập thư viện ảnh trong Cài đặt của điện thoại' };
  }

  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ['images', 'videos'],
    allowsMultipleSelection: true,
    selectionLimit: remaining,
  });
  if (result.canceled) return { files: [], error: '' };

  const picked = result.assets.map(toFile);
  const accepted = picked.filter((file) => !file.fileSize || file.fileSize <= MAX_FILE_BYTES);
  const files = accepted.slice(0, remaining);
  if (accepted.length < picked.length) {
    return { files, error: 'Có file lớn hơn 50 MB nên chưa được thêm' };
  }
  if (files.length < accepted.length) {
    return { files, error: `Mỗi tin gửi tối đa ${MAX_FILES} file` };
  }
  return { files, error: '' };
};
