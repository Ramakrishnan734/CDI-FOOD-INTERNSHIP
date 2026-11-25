// frontend/src/pages/Inventory.jsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

export default function Inventory() {
  const navigate = useNavigate()
  const name = localStorage.getItem('name')
  const role = localStorage.getItem('role')

  const [stock, setStock] = useState([])
  const [ledger, setLedger] = useState([])
  const [ledgerItem, setLedgerItem] = useState('')
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)

  // Purchase form
  const [purchase, setPurchase] = useState({
    supplier_name: 'General Supplier',
    item_code: '',
    qty: '',
    unit_rate: '',
    order_date: new Date().toISOString().split('T')[0],
  })

  useEffect(() => { fetchStock() }, [])

    async function fetchStock() {
      setError(null)

    try {
      const res = await api.get('/inventory/balance')
      setStock(res.data)
    } catch {
      setError('Failed to load stock')
    }
  }

  async function fetchLedger(code) {
    setError(null)
    setLedger([])
    setLedgerItem(code)

    try {
      const res = await api.get('/inventory/ledger', {
        params: { item_code: code },
      })
      setLedger(res.data.movements || [])
    } catch {
      setError('Failed to load ledger')
    }
  }

  async function handlePurchase(e) {
    e.preventDefault()
    setMessage(null); setError(null)
    try {
      const payload = {
        client_request_id: `PUR-${Date.now()}`,
        supplier_name: purchase.supplier_name,
        order_date: purchase.order_date,
        lines: [{
          item_code: purchase.item_code,
          qty: parseFloat(purchase.qty),
          unit_rate: parseFloat(purchase.unit_rate),
        }],
      }
      await api.post('/inventory/purchase', payload)
      setMessage(`Purchase recorded: ${purchase.qty} units of ${purchase.item_code}`)
      setPurchase(p => ({ ...p, item_code: '', qty: '', unit_rate: '' }))
      fetchStock()
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }
  }

  function logout() {
    localStorage.clear()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-gray-800 text-white px-4 py-3 flex justify-between items-center">
        <div>
          <div className="font-bold text-lg">CDI Food ERP — Inventory</div>
          <div className="text-gray-400 text-xs">{name}</div>
        </div>
        <div className="flex gap-2">
          {role === 'admin' && (
            <button onClick={() => navigate('/admin')}
              className="bg-gray-700 text-xs px-3 py-1 rounded">Admin</button>
          )}
          <button onClick={() => navigate('/production')}
            className="bg-gray-700 text-xs px-3 py-1 rounded">Production</button>
          <button onClick={() => navigate('/reports')}
            className="bg-gray-700 text-xs px-3 py-1 rounded">Reports</button>
          <button onClick={logout}
            className="bg-gray-700 text-xs px-3 py-1 rounded">Logout</button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-4 space-y-4">

        {message && <div className="bg-green-50 text-green-700 text-sm rounded p-3">{message}</div>}
        {error && <div className="bg-red-50 text-red-600 text-sm rounded p-3">{error}</div>}

        {/* Stock Balance */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="mb-3">
            <h2 className="font-semibold text-gray-700">Stock Balance</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="pb-2 pr-4">Item Code</th>
                  <th className="pb-2 pr-4">Name</th>
                  <th className="pb-2 pr-4">Balance</th>
                  <th className="pb-2">Unit</th>
                  <th className="pb-2"></th>
                </tr>
              </thead>
              <tbody>
                {stock.map(item => (
                  <tr key={item.code} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-mono text-xs">{item.code}</td>
                    <td className="py-2 pr-4">{item.name}</td>
                    <td className="py-2 pr-4 font-semibold">{item.balance}</td>
                    <td className="py-2">{item.unit}</td>
                    <td className="py-2">
                      <button
                        onClick={() => { setLedgerItem(item.code); fetchLedger(item.code) }}
                        className="text-xs text-blue-600 hover:underline">
                        Ledger
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Purchase Form — admin/production only */}
        {(role === 'admin' || role === 'production') && (
          <div className="bg-white rounded-xl shadow-sm p-4">
            <h2 className="font-semibold text-gray-700 mb-3">Record Purchase</h2>
            <form onSubmit={handlePurchase} className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500">Item Code</label>
                <input
                  value={purchase.item_code}
                  onChange={e => setPurchase(p => ({ ...p, item_code: e.target.value }))}
                  required placeholder="e.g. RM-FLOUR"
                  className="w-full border rounded px-2 py-1 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Quantity</label>
                <input
                  type="number" step="0.001"
                  value={purchase.qty}
                  onChange={e => setPurchase(p => ({ ...p, qty: e.target.value }))}
                  required placeholder="e.g. 60"
                  className="w-full border rounded px-2 py-1 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Unit Rate (₹)</label>
                <input
                  type="number" step="0.01"
                  value={purchase.unit_rate}
                  onChange={e => setPurchase(p => ({ ...p, unit_rate: e.target.value }))}
                  required placeholder="e.g. 45"
                  className="w-full border rounded px-2 py-1 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Order Date</label>
                <input
                  type="date"
                  value={purchase.order_date}
                  onChange={e => setPurchase(p => ({ ...p, order_date: e.target.value }))}
                  required
                  className="w-full border rounded px-2 py-1 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div className="col-span-2">
                <button type="submit"
                  className="bg-blue-600 text-white text-sm px-4 py-2 rounded hover:bg-blue-700">
                  Record Purchase
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Stock Ledger */}
        {ledger.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-4">
            <h2 className="font-semibold text-gray-700 mb-3">Stock Ledger — {ledgerItem}</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="pb-2 pr-3">Date</th>
                    <th className="pb-2 pr-3">Type</th>
                    <th className="pb-2 pr-3">Reference</th>
                    <th className="pb-2 pr-3">In</th>
                    <th className="pb-2 pr-3">Out</th>
                    <th className="pb-2">Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {ledger.map((row, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="py-1 pr-3 text-xs">{row.date}</td>
                      <td className="py-1 pr-3 text-xs">{row.movement_type}</td>
                      <td className="py-1 pr-3 text-xs font-mono">
                          {row.ref_type} {row.ref_id}
                      </td>
                      <td className="py-1 pr-3 text-green-700">{row.qty_in > 0 ? row.qty_in : ''}</td>
                      <td className="py-1 pr-3 text-red-600">{row.qty_out > 0 ? row.qty_out : ''}</td>
                      <td className="py-1 font-semibold">{row.running_balance}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
