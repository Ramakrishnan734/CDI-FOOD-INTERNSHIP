
import { useState } from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { useAuth } from '../auth/AuthContext';
import OrderEntryScreen from './OrderEntryScreen';

export default function HomeScreen() {
  const { user, logout } = useAuth();
  const [showOrderEntry, setShowOrderEntry] = useState(false);

  if (showOrderEntry) {
    return (
      <OrderEntryScreen
        onBack={() => setShowOrderEntry(false)}
      />
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.brand}>CDI FOOD ERP</Text>
      <Text style={styles.heading}>
        Welcome, {user?.name || 'Salesman'}
      </Text>

      <View style={styles.roleCard}>
        <Text style={styles.label}>Signed in as</Text>
        <Text style={styles.role}>Salesman</Text>
      </View>

      <Pressable
        style={styles.orderButton}
        onPress={() => setShowOrderEntry(true)}
        accessibilityRole="button"
      >
        <Text style={styles.buttonText}>Create Sales Order</Text>
      </Pressable>

      <Pressable
        style={styles.logoutButton}
        onPress={() => void logout()}
        accessibilityRole="button"
      >
        <Text style={styles.logoutText}>Log Out</Text>
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
  orderButton: {
    alignItems: 'center',
    backgroundColor: '#2563EB',
    borderRadius: 10,
    justifyContent: 'center',
    marginTop: 28,
    minHeight: 52,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  logoutButton: {
    alignItems: 'center',
    backgroundColor: '#111827',
    borderRadius: 10,
    justifyContent: 'center',
    marginTop: 14,
    minHeight: 50,
  },
  logoutText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});
