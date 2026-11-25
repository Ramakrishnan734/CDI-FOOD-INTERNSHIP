
import { Platform } from 'react-native';

const defaultApiUrl =
  Platform.OS === 'android'
    ? 'http://127.0.0.1:8001'
    : 'http://localhost:8001';

export const API_BASE_URL = (
  process.env.EXPO_PUBLIC_API_URL || defaultApiUrl
).replace(/\/+$/, '');
