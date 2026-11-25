import { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { useAuth } from '../auth/AuthContext';

export default function LoginScreen() {
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function handleLogin() {
    setError('');

    if (!email.trim() || !password) {
      setError('Enter your email and password.');
      return;
    }

    setSubmitting(true);

    try {
      await login(email, password);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Unable to sign in.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.brand}>CDI FOOD ERP</Text>
        <Text style={styles.heading}>Salesman Login</Text>
        <Text style={styles.subtitle}>
          Sign in with your assigned Salesman account.
        </Text>
      </View>

      <View style={styles.form}>
        <Text style={styles.label}>Email</Text>
        <TextInput
          style={styles.input}
          value={email}
          onChangeText={setEmail}
          placeholder="Enter your email"
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          textContentType="emailAddress"
          editable={!submitting}
        />

        <Text style={styles.label}>Password</Text>
        <View style={styles.passwordRow}>
          <TextInput
            style={styles.passwordInput}
            value={password}
            onChangeText={setPassword}
            placeholder="Enter your password"
            secureTextEntry={!showPassword}
            autoCapitalize="none"
            textContentType="password"
            editable={!submitting}
          />
          <Pressable
            onPress={() => setShowPassword((value) => !value)}
            accessibilityRole="button"
            accessibilityLabel={showPassword ? 'Hide password' : 'Show password'}
          >
            <Text style={styles.showPassword}>
              {showPassword ? 'Hide' : 'Show'}
            </Text>
          </Pressable>
        </View>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Pressable
          style={[styles.button, submitting && styles.buttonDisabled]}
          onPress={() => void handleLogin()}
          disabled={submitting}
          accessibilityRole="button"
        >
          {submitting ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.buttonText}>Sign In</Text>
          )}
        </Pressable>
      </View>

      <Text style={styles.footer}>
        Authorized Salesman accounts only
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F7FA',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  header: {
    marginBottom: 32,
  },
  brand: {
    color: '#2563EB',
    fontSize: 14,
    fontWeight: '800',
    letterSpacing: 1.5,
    marginBottom: 12,
  },
  heading: {
    color: '#111827',
    fontSize: 28,
    fontWeight: '700',
  },
  subtitle: {
    color: '#6B7280',
    fontSize: 15,
    marginTop: 8,
    lineHeight: 22,
  },
  form: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 20,
  },
  label: {
    color: '#374151',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
    marginTop: 12,
  },
  input: {
    backgroundColor: '#F9FAFB',
    borderColor: '#E5E7EB',
    borderRadius: 10,
    borderWidth: 1,
    color: '#111827',
    fontSize: 16,
    paddingHorizontal: 14,
    paddingVertical: 13,
  },
  passwordRow: {
    alignItems: 'center',
    backgroundColor: '#F9FAFB',
    borderColor: '#E5E7EB',
    borderRadius: 10,
    borderWidth: 1,
    flexDirection: 'row',
    paddingHorizontal: 14,
  },
  passwordInput: {
    flex: 1,
    color: '#111827',
    fontSize: 16,
    paddingVertical: 13,
  },
  showPassword: {
    color: '#2563EB',
    fontWeight: '600',
    paddingLeft: 12,
  },
  error: {
    color: '#B91C1C',
    fontSize: 14,
    lineHeight: 20,
    marginTop: 14,
  },
  button: {
    alignItems: 'center',
    backgroundColor: '#2563EB',
    borderRadius: 10,
    justifyContent: 'center',
    marginTop: 24,
    minHeight: 50,
  },
  buttonDisabled: {
    opacity: 0.65,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  footer: {
    color: '#9CA3AF',
    fontSize: 12,
    marginTop: 24,
    textAlign: 'center',
  },
});
