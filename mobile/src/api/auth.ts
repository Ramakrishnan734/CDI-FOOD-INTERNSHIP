import { API_BASE_URL } from '../config/api';
import type { AuthUser } from '../storage/secureStorage';

type LoginResponse = {
  token: string;
  user_id: number;
  name: string;
  role: string;
};

export async function loginRequest(
  email: string,
  password: string,
): Promise<{ token: string; user: AuthUser }> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new Error(
      `Cannot connect to CDI Food ERP at ${API_BASE_URL}. Check that the backend is running and the API URL is correct.`,
    );
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      typeof data?.detail === 'string'
        ? data.detail
        : `Login failed (${response.status})`;

    throw new Error(detail);
  }

  const result = data as LoginResponse;

  if (
    !result?.token ||
    typeof result.user_id !== 'number' ||
    typeof result.name !== 'string' ||
    typeof result.role !== 'string'
  ) {
    throw new Error('The backend returned an unexpected login response.');
  }

  if (result.role !== 'salesman') {
    throw new Error(
      'This account is not authorized for the Salesman mobile app.',
    );
  }

  return {
    token: result.token,
    user: {
      user_id: result.user_id,
      name: result.name,
      role: result.role,
    },
  };
}
