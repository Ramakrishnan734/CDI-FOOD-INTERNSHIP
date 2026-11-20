// frontend/src/api/sales.js
import api from './client'

export const createOrder = (data) => api.post('/sales/order', data)
export const getBalance = () => api.get('/inventory/balance')
export const approveOrder = (id) => api.post(`/sales/${id}/approve`)
export const dispatchOrder = (id) => api.post(`/sales/${id}/dispatch`)
export const recordPayment = (id, data) => api.post(`/sales/${id}/payment`, data)
export const getInvoicePdf = (id) => api.get(`/sales/${id}/invoice/pdf`, { responseType: 'blob' })