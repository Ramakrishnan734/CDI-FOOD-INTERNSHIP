
import { API_BASE_URL } from '../config/api';
import { loadSession } from '../storage/secureStorage';

export type SalesCustomer = {
  id: number;
  name: string;
  state_code: string;
};

export type FinishedGood = {
  id: number;
  code: string;
  name: string;
  unit: string;
  selling_price: string | null;
  stock_balance: string;
  can_order: boolean;
};

async function salesRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const session = await loadSession();

  if (!session?.token) {
    throw new Error('Your session has expired. Please log in again.');
  }

  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        Authorization: `Bearer ${session.token}`,
        ...options.headers,
      },
    });
  } catch {
    throw new Error(
      `Cannot connect to CDI Food ERP at ${API_BASE_URL}.`,
    );
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      typeof data?.detail === 'string'
        ? data.detail
        : `Request failed (${response.status})`;

    throw new Error(detail);
  }

  return data as T;
}

export function fetchSalesCustomers(): Promise<SalesCustomer[]> {
  return salesRequest<SalesCustomer[]>('/sales/customers');
}

export function fetchFinishedGoods(): Promise<FinishedGood[]> {
  return salesRequest<FinishedGood[]>('/sales/finished-goods');
}

export type CreateSalesOrderPayload = {
  customer_id: number;
  order_date: string;
  lines: {
    item_code: string;
    qty: string;
    unit_price: string;
  }[];
};

export type CreateSalesOrderResponse = {
  order_id: number;
  order_number: string;
  customer_name: string;
  status: string;
  taxable_value: string;
};

export function createSalesOrder(
  payload: CreateSalesOrderPayload,
): Promise<CreateSalesOrderResponse> {
  return salesRequest<CreateSalesOrderResponse>('/sales/order', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
