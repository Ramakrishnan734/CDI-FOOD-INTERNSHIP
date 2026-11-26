// frontend/src/pages/AdminDashboard.jsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { approveOrder, dispatchOrder, recordPayment, getInvoicePdf } from '../api/sales'

export default function AdminDashboard() {
  const navigate = useNavigate()
  const name = localStorage.getItem('name')

  const [orders, setOrders] = useState([])
  const [stock, setStock] = useState([])
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)
  const [paymentOrderId, setPaymentOrderId] = useState(null)
  const [paymentAmount, setPaymentAmount] = useState('')

  useEffect(() => { fetchData() }, [])

  async function fetchData() {
    try {
      const [ordersRes, stockRes] = await Promise.all([
        api.get('/sales/orders'),
        api.get('/inventory/balance'),
      ])
      setOrders(ordersRes.data)
      setStock(stockRes.data)
    } catch {
      setError('Failed to load data')
    }
  }

  function logout() {
    localStorage.clear()
    navigate('/login')
  }

  async function handleApprove(id) {
    setMessage(null); setError(null)
    try {
      const res = await approveOrder(id)
      setMessage(`Invoice ${res.data.invoice_number} generated. Total: ₹${res.data.invoice_total}`)
      fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Approval failed')
    }
  }

  async function handleDispatch(id) {
    setMessage(null); setError(null)
    try {
      await dispatchOrder(id)
      setMessage(`Order ${id} dispatched successfully`)
      fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Dispatch failed')
    }
  }

  async function handlePayment(e) {
    e.preventDefault()
    setMessage(null); setError(null)
    try {
      const res = await recordPayment(paymentOrderId, {
        amount: parseFloat(paymentAmount),
        payment_date: new Date().toISOString().split('T')[0],
        reference: `PAY-${Date.now()}`,
      })
      setMessage(`Payment ₹${paymentAmount} recorded. Outstanding: ₹${res.data.new_outstanding}`)
      setPaymentOrderId(null)
      setPaymentAmount('')
      fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Payment failed')
    }
  }

  async function handleDownloadPdf(id, invoiceNumber) {
    try {
      const res = await getInvoicePdf(id)
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `${invoiceNumber}.pdf`
      a.click()
    } catch {
      setError('Failed to download invoice')
    }
  }

  const statusColor = {
    pending: 'bg-yellow-100 text-yellow-700',
    approved: 'bg-blue-100 text-blue-700',
    dispatched: 'bg-green-100 text-green-700',
    cancelled: 'bg-red-100 text-red-700',
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gray-800 text-white px-4 py-3 flex justify-between items-center">
        <div>
          <div className="font-bold text-lg">CDI Food ERP — Admin</div>
          <div className="text-gray-400 text-xs">{name}</div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => navigate('/inventory')}
            className="bg-gray-700 text-xs px-3 py-1 rounded">
            Inventory
          </button>
          <button onClick={() => navigate('/production')}
            className="bg-gray-700 text-xs px-3 py-1 rounded">
            Production
          </button>
          <button onClick={() => navigate('/reports')}
            className="bg-gray-700 text-xs px-3 py-1 rounded">
            Reports
          </button>
          <button onClick={logout}
            className="bg-gray-700 text-xs px-3 py-1 rounded">
            Logout
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-4 space-y-4">

        {message && (
          <div className="bg-green-50 text-green-700 text-sm rounded p-3">{message}</div>
        )}
        {error && (
          <div className="bg-red-50 text-red-600 text-sm rounded p-3">{error}</div>
        )}

        {/* Stock summary */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h2 className="font-semibold text-gray-700 mb-3">Current Stock</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {stock.map(item => (
              <div key={item.code} className="bg-gray-50 rounded-lg p-3">
                <div className="text-xs text-gray-500">{item.code}</div>
                <div className="font-semibold text-gray-800">{item.balance}</div>
                <div className="text-xs text-gray-500">{item.unit}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Orders */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex justify-between items-center mb-3">
            <h2 className="font-semibold text-gray-700">Sales Orders</h2>
          </div>

          {orders.length === 0 && (
            <p className="text-sm text-gray-400">No orders yet.</p>
          )}

          <div className="space-y-3">
            {orders.map(order => (
              <div key={order.id} className="border rounded-lg p-3">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <div className="font-medium text-sm">{order.order_number}</div>
                    <div className="text-xs text-gray-500">{order.customer_name} · {order.order_date}</div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${statusColor[order.status]}`}>
                    {order.status}
                  </span>
                </div>

                <div className="text-sm text-gray-600 mb-2">
                  {order.invoice_number && (
                    <span className="mr-3">Invoice: {order.invoice_number}</span>
                  )}
                  {order.invoice_total == null && order.taxable_value == null ? (
                      <span>Total: Not invoiced</span>
                    ) : (
                      <span>Total: ₹{order.invoice_total ?? order.taxable_value}</span>
                    )}
                  {order.outstanding && (
                    <span className="ml-3 text-orange-600">Outstanding: ₹{order.outstanding}</span>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  {order.status === 'pending' && (
                    <button onClick={() => handleApprove(order.id)}
                      className="bg-blue-600 text-white text-xs px-3 py-1 rounded hover:bg-blue-700">
                      Approve & Invoice
                    </button>
                  )}
                  {order.status === 'approved' && (
                    <>
                      <button onClick={() => handleDispatch(order.id)}
                        className="bg-green-600 text-white text-xs px-3 py-1 rounded hover:bg-green-700">
                        Dispatch
                      </button>
                      <button onClick={() => handleDownloadPdf(order.id, order.invoice_number)}
                        className="bg-gray-600 text-white text-xs px-3 py-1 rounded hover:bg-gray-700">
                        Download Invoice
                      </button>
                    </>
                  )}
                  {order.status === 'dispatched' && (
                    <>
                      <button onClick={() => setPaymentOrderId(order.id)}
                        className="bg-orange-500 text-white text-xs px-3 py-1 rounded hover:bg-orange-600">
                        Record Payment
                      </button>
                      <button onClick={() => handleDownloadPdf(order.id, order.invoice_number)}
                        className="bg-gray-600 text-white text-xs px-3 py-1 rounded hover:bg-gray-700">
                        Download Invoice
                      </button>
                    </>
                  )}
                </div>

                {/* Inline payment form */}
                {paymentOrderId === order.id && (
                  <form onSubmit={handlePayment} className="mt-3 flex gap-2 items-center">
                    <input
                      type="number"
                      step="0.01"
                      value={paymentAmount}
                      onChange={e => setPaymentAmount(e.target.value)}
                      required
                      min="1"
                      placeholder="Amount ₹"
                      className="border border-gray-300 rounded px-2 py-1 text-sm w-32 focus:outline-none focus:ring-2 focus:ring-orange-400"
                    />
                    <button type="submit"
                      className="bg-orange-500 text-white text-xs px-3 py-1 rounded hover:bg-orange-600">
                      Record
                    </button>
                    <button type="button" onClick={() => setPaymentOrderId(null)}
                      className="text-xs text-gray-500 hover:underline">
                      Cancel
                    </button>
                  </form>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}