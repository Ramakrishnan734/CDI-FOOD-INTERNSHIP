// frontend/src/pages/SalesmanDashboard.jsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { createOrder, getBalance } from '../api/sales'

const CUSTOMERS = [
  { id: 1, name: 'Retailer A (Tamil Nadu)' },
  { id: 2, name: 'Distributor B (Karnataka)' },
]

export default function SalesmanDashboard() {
  const navigate = useNavigate()
  const name = localStorage.getItem('name')
  const role = localStorage.getItem('role')

  const [stock, setStock] = useState([])
  const [customerId, setCustomerId] = useState(1)
  const [qty, setQty] = useState('')
  const [unitPrice] = useState(50)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getBalance().then(res => {
      setStock(res.data.filter(i => i.type === 'finished'))
    })
  }, [])

  function logout() {
    localStorage.clear()
    navigate('/login')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setMessage(null)
    setError(null)
    setLoading(true)
    try {
      const res = await createOrder({
        customer_id: parseInt(customerId),
        order_date: new Date().toISOString().split('T')[0],
        lines: [{ item_code: 'FG-MRK200', qty: parseFloat(qty), unit_price: unitPrice }],
      })
      setMessage(`Order ${res.data.order_number} placed successfully! Taxable value: ₹${res.data.taxable_value}`)
      setQty('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to place order')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-blue-600 text-white px-4 py-3 flex justify-between items-center">
        <div>
          <div className="font-bold text-lg">CDI Food ERP</div>
          <div className="text-blue-200 text-xs">{name} · {role}</div>
        </div>
        <div className="flex gap-2">
          {role === 'admin' && (
            <button onClick={() => navigate('/admin')}
              className="bg-white text-blue-600 text-xs px-3 py-1 rounded font-medium">
              Admin View
            </button>
          )}
          <button onClick={logout}
            className="bg-blue-700 text-xs px-3 py-1 rounded">
            Logout
          </button>
        </div>
      </div>

      <div className="max-w-lg mx-auto p-4 space-y-4">

        {/* Stock summary */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h2 className="font-semibold text-gray-700 mb-3">Finished Goods Stock</h2>
          {stock.map(item => (
            <div key={item.code} className="flex justify-between text-sm py-1 border-b last:border-0">
              <span className="text-gray-600">{item.name}</span>
              <span className="font-medium">{item.balance} {item.unit}</span>
            </div>
          ))}
        </div>

        {/* Place order form */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h2 className="font-semibold text-gray-700 mb-3">Place New Order</h2>

          {message && (
            <div className="bg-green-50 text-green-700 text-sm rounded p-3 mb-3">{message}</div>
          )}
          {error && (
            <div className="bg-red-50 text-red-600 text-sm rounded p-3 mb-3">{error}</div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Customer</label>
              <select
                value={customerId}
                onChange={e => setCustomerId(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {CUSTOMERS.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Product</label>
              <input
                type="text"
                value="Murukku 200g (FG-MRK200)"
                disabled
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Quantity (packets)</label>
              <input
                type="number"
                value={qty}
                onChange={e => setQty(e.target.value)}
                required
                min="1"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g. 150"
              />
            </div>
            <div className="flex justify-between text-sm text-gray-500 bg-gray-50 rounded p-2">
              <span>Unit price</span>
              <span className="font-medium">₹{unitPrice}.00</span>
            </div>
            {qty && (
              <div className="flex justify-between text-sm bg-blue-50 text-blue-700 rounded p-2">
                <span>Taxable value</span>
                <span className="font-medium">₹{(qty * unitPrice).toLocaleString()}.00</span>
              </div>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Placing order...' : 'Place Order'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}