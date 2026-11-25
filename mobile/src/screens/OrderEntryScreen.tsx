
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import {
  createSalesOrder,
  fetchFinishedGoods,
  fetchSalesCustomers,
  type FinishedGood,
  type SalesCustomer,
} from '../api/sales';

type Props = {
  onBack: () => void;
};

function getLocalDate(): string {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');

  return `${year}-${month}-${day}`;
}

export default function OrderEntryScreen({ onBack }: Props) {
  const [customers, setCustomers] = useState<SalesCustomer[]>([]);
  const [goods, setGoods] = useState<FinishedGood[]>([]);
  const [customerId, setCustomerId] = useState<number | null>(null);
  const [itemCode, setItemCode] = useState<string | null>(null);
  const [quantity, setQuantity] = useState('1');

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    async function loadCatalogs() {
      try {
        const [customerData, goodsData] = await Promise.all([
          fetchSalesCustomers(),
          fetchFinishedGoods(),
        ]);

        setCustomers(customerData);
        setGoods(goodsData);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : 'Unable to load the order catalog.',
        );
      } finally {
        setLoading(false);
      }
    }

    void loadCatalogs();
  }, []);

  const selectedCustomer =
    customers.find((customer) => customer.id === customerId) ?? null;

  const selectedGood =
    goods.find((good) => good.code === itemCode) ?? null;

  async function submitOrder() {
    setError('');
    setSuccess('');

    if (!customerId) {
      setError('Please select a customer.');
      return;
    }

    if (!selectedGood) {
      setError('Please select a finished good.');
      return;
    }

    const parsedQuantity = Number(quantity);

    if (!Number.isFinite(parsedQuantity) || parsedQuantity <= 0) {
      setError('Enter a valid quantity greater than zero.');
      return;
    }

    if (!selectedGood.selling_price) {
      setError('This item does not have a configured selling price.');
      return;
    }

    setSubmitting(true);

    try {
      const result = await createSalesOrder({
        customer_id: customerId,
        order_date: getLocalDate(),
        lines: [
          {
            item_code: selectedGood.code,
            qty: quantity,
            unit_price: selectedGood.selling_price,
          },
        ],
      });

      setSuccess(
        `Order ${result.order_number} created successfully.`,
      );
      setQuantity('1');
      setItemCode(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Order submission failed.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2563EB" />
        <Text style={styles.loadingText}>Loading order catalog...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      <Pressable onPress={onBack} style={styles.backButton}>
        <Text style={styles.backText}>‹ Back to Home</Text>
      </Pressable>

      <Text style={styles.brand}>CDI FOOD ERP</Text>
      <Text style={styles.heading}>Create Sales Order</Text>
      <Text style={styles.subtitle}>
        Select a customer, product and quantity.
      </Text>

      {!!error && <Text style={styles.error}>{error}</Text>}
      {!!success && <Text style={styles.success}>{success}</Text>}

      <Text style={styles.sectionTitle}>1. Select Customer</Text>

      {customers.length === 0 ? (
        <Text style={styles.emptyText}>No active customers found.</Text>
      ) : (
        customers.map((customer) => (
          <Pressable
            key={customer.id}
            style={[
              styles.option,
              customerId === customer.id && styles.selectedOption,
            ]}
            onPress={() => setCustomerId(customer.id)}
          >
            <Text style={styles.optionTitle}>{customer.name}</Text>
            <Text style={styles.optionSub}>
              State code: {customer.state_code}
            </Text>
          </Pressable>
        ))
      )}

      <Text style={styles.sectionTitle}>2. Select Finished Good</Text>

      {goods.length === 0 ? (
        <Text style={styles.emptyText}>No finished goods found.</Text>
      ) : (
        goods.map((good) => {
          const isSelected = itemCode === good.code;
          const hasPrice = good.selling_price !== null;

          return (
            <Pressable
              key={good.id}
              style={[
                styles.option,
                isSelected && styles.selectedOption,
              ]}
              onPress={() => setItemCode(good.code)}
            >
              <Text style={styles.optionTitle}>
                {good.name} ({good.code})
              </Text>

              <Text style={styles.optionSub}>
                Price:{' '}
                {hasPrice
                  ? `₹${good.selling_price} / ${good.unit}`
                  : 'Not configured'}
              </Text>

              <Text style={styles.optionSub}>
                Stock: {good.stock_balance} {good.unit}
              </Text>

              {!hasPrice && (
                <Text style={styles.warning}>
                  Cannot order — price not configured
                </Text>
              )}
            </Pressable>
          );
        })
      )}

      <Text style={styles.sectionTitle}>3. Quantity</Text>

      <TextInput
        style={styles.quantityInput}
        value={quantity}
        onChangeText={setQuantity}
        keyboardType="decimal-pad"
        placeholder="Enter quantity"
        accessibilityLabel="Order quantity"
      />

      {selectedCustomer && selectedGood && (
        <View style={styles.summary}>
          <Text style={styles.summaryTitle}>Order Summary</Text>
          <Text style={styles.summaryText}>
            Customer: {selectedCustomer.name}
          </Text>
          <Text style={styles.summaryText}>
            Product: {selectedGood.name}
          </Text>
          <Text style={styles.summaryText}>
            Quantity: {quantity} {selectedGood.unit}
          </Text>
          <Text style={styles.summaryText}>
            Unit price:{' '}
            {selectedGood.selling_price
              ? `₹${selectedGood.selling_price}`
              : 'Not configured'}
          </Text>
        </View>
      )}

      <Pressable
        style={[
          styles.submitButton,
          submitting && styles.disabledButton,
        ]}
        onPress={() => void submitOrder()}
        disabled={submitting}
      >
        {submitting ? (
          <ActivityIndicator color="#FFFFFF" />
        ) : (
          <Text style={styles.submitText}>Submit Order</Text>
        )}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#F5F7FA',
  },
  container: {
    padding: 20,
    paddingBottom: 40,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F5F7FA',
  },
  loadingText: {
    marginTop: 12,
    color: '#6B7280',
  },
  backButton: {
    alignSelf: 'flex-start',
    paddingVertical: 8,
    marginBottom: 12,
  },
  backText: {
    color: '#2563EB',
    fontSize: 16,
    fontWeight: '600',
  },
  brand: {
    color: '#2563EB',
    fontSize: 13,
    fontWeight: '800',
    letterSpacing: 1.5,
  },
  heading: {
    color: '#111827',
    fontSize: 25,
    fontWeight: '700',
    marginTop: 8,
  },
  subtitle: {
    color: '#6B7280',
    fontSize: 14,
    marginTop: 6,
    marginBottom: 18,
  },
  sectionTitle: {
    color: '#111827',
    fontSize: 17,
    fontWeight: '700',
    marginTop: 22,
    marginBottom: 10,
  },
  option: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
  },
  selectedOption: {
    borderColor: '#2563EB',
    backgroundColor: '#EFF6FF',
  },
  optionTitle: {
    color: '#111827',
    fontSize: 15,
    fontWeight: '600',
  },
  optionSub: {
    color: '#6B7280',
    fontSize: 13,
    marginTop: 5,
  },
  warning: {
    color: '#B45309',
    fontSize: 12,
    marginTop: 5,
  },
  emptyText: {
    color: '#6B7280',
    fontSize: 14,
  },
  quantityInput: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#D1D5DB',
    borderRadius: 10,
    paddingHorizontal: 14,
    minHeight: 48,
    color: '#111827',
    fontSize: 16,
  },
  summary: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginTop: 20,
  },
  summaryTitle: {
    color: '#111827',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 8,
  },
  summaryText: {
    color: '#4B5563',
    fontSize: 14,
    marginTop: 4,
  },
  error: {
    color: '#B91C1C',
    backgroundColor: '#FEE2E2',
    borderRadius: 8,
    padding: 12,
    marginTop: 12,
  },
  success: {
    color: '#166534',
    backgroundColor: '#DCFCE7',
    borderRadius: 8,
    padding: 12,
    marginTop: 12,
  },
  submitButton: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#2563EB',
    borderRadius: 10,
    minHeight: 52,
    marginTop: 24,
  },
  disabledButton: {
    opacity: 0.6,
  },
  submitText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});
