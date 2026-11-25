import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'cdi_salesman_token';
const USER_KEY = 'cdi_salesman_user';

export type AuthUser = {
  user_id: number;
  name: string;
  role: string;
};

export async function saveSession(
  token: string,
  user: AuthUser,
): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
  await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user));
}

export async function loadSession(): Promise<{
  token: string;
  user: AuthUser;
} | null> {
  const token = await SecureStore.getItemAsync(TOKEN_KEY);
  const userJson = await SecureStore.getItemAsync(USER_KEY);

  if (!token || !userJson) {
    return null;
  }

  try {
    const user = JSON.parse(userJson) as AuthUser;

    if (
      typeof user.user_id !== 'number' ||
      typeof user.name !== 'string' ||
      user.role !== 'salesman'
    ) {
      await clearSession();
      return null;
    }

    return { token, user };
  } catch {
    await clearSession();
    return null;
  }
}

export async function clearSession(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(USER_KEY);
}
