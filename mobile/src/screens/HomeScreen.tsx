import {
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { useAuth } from '../auth/AuthContext';

export default function HomeScreen() {
  const { user, logout } = useAuth();

  return (
    <View style={styles.container}>
      <Text style={styles.brand}>CDI FOOD ERP</Text>
      <Text style={styles.heading}>Welcome, {user?.name || 'Salesman'}</Text>

      <View style={styles.roleCard}>
        <Text style={styles.label}>Signed in as</Text>
        <Text style={styles.role}>Salesman</Text>
      </View>

      <Text style={styles.note}>
        Your Salesman workspace is ready. Order-entry features will be added
        in the next approved phase.
      </Text>

      <Pressable
        style={styles.button}
        onPress={() => void logout()}
        accessibilityRole="button"
      >
        <Text style={styles.buttonText}>Log Out</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F7FA',
    justifyContent: 'center',
    padding: 24,
  },
  brand: {
    color: '#2563EB',
    fontSize: 14,
    fontWeight: '800',
    letterSpacing: 1.5,
    marginBottom: 16,
  },
  heading: {
    color: '#111827',
    fontSize: 26,
    fontWeight: '700',
  },
  roleCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    marginTop: 24,
    padding: 20,
  },
  label: {
    color: '#6B7280',
    fontSize: 14,
  },
  role: {
    color: '#111827',
    fontSize: 20,
    fontWeight: '700',
    marginTop: 6,
    textTransform: 'capitalize',
  },
  note: {
    color: '#6B7280',
    fontSize: 15,
    lineHeight: 23,
    marginTop: 20,
  },
  button: {
    alignItems: 'center',
    backgroundColor: '#111827',
    borderRadius: 10,
    justifyContent: 'center',
    marginTop: 32,
    minHeight: 50,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});
