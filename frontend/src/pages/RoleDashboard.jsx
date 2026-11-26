import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

const ROLE_INFO = {
  owner: {
    title: 'Owner Dashboard',
    subtitle: 'Business-wide overview · View only',
    links: [
      { label: 'Reports', path: '/reports' },
      { label: 'Inventory & Ledger', path: '/inventory' },
    ],
  },
  auditor: {
    title: 'Accountant Dashboard',
    subtitle: 'Financial and audit visibility · Read only',
    links: [
      { label: 'Financial Reports', path: '/reports' },
      { label: 'Inventory & Ledger', path: '/inventory' },
    ],
  },
}

function money(value) {
  const amount = Number(value || 0)
  return amount.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 })
}

export default function RoleDashboard({ role }) {
  const navigate = useNavigate()
  const name = localStorage.getItem('name') || ''
  const info = ROLE_INFO[role]
  const [orders, setOrders] = useState([])
  const [stock, setStock] = useState([])
  const [runs, setRuns] = useState([])
  const [payments, setPayments] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [pdfError, setPdfError] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([
      api.get('/sales/orders'),
      api.get('/inventory/balance'),
      api.get('/production/runs'),
      api.get('/sales/payments'),
    ]).then(([ordersRes, stockRes, runsRes, paymentsRes]) => {
      if (!active) return
      setOrders(ordersRes.data)
      setStock(stockRes.data)
      setRuns(runsRes.data)
      setPayments(paymentsRes.data)
    }).catch(() => {
      if (active) setError('Some dashboard information could not be loaded. Use Reports to view available exports.')
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  async function downloadInvoice(order) {
    setPdfError('')
    try {
      const response = await api.get(`/sales/${order.id}/invoice/pdf`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.download = `${order.invoice_number || order.order_number}.pdf`
      link.click()
      window.URL.revokeObjectURL(url)
    } catch {
      setPdfError(`Could not download invoice for ${order.order_number}.`)
    }
  }

  function logout() {
    localStorage.clear()
    navigate('/login')
  }

  const invoicedSales = orders.reduce((sum, order) => sum + Number(order.invoice_total || 0), 0)
  const outstanding = orders.reduce((sum, order) => sum + Number(order.outstanding || 0), 0)
  const stockItems = stock.length
  const postedRuns = runs.filter(run => run.status === 'posted').length
  const monthlySales = Object.entries(orders.reduce((totals, order) => {
    if (order.invoice_total && order.order_date) {
      const month = order.order_date.slice(0, 7)
      totals[month] = (totals[month] || 0) + Number(order.invoice_total)
    }
    return totals
  }, {})).sort(([a], [b]) => a.localeCompare(b)).slice(-6)
  const maxMonthlySales = Math.max(1, ...monthlySales.map(([, total]) => total))

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-gray-800 text-white px-4 py-3 flex flex-wrap justify-between items-center gap-3">
        <div>
          <div className="font-bold text-lg">CDI Food ERP — {info.title}</div>
          <div className="text-gray-300 text-xs">{name} · {info.subtitle}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          {info.links.map(link => (
            <button key={link.path} onClick={() => navigate(link.path)} className="bg-gray-700 text-xs px-3 py-1 rounded">
              {link.label}
            </button>
          ))}
          <button onClick={logout} className="bg-gray-700 text-xs px-3 py-1 rounded">Logout</button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-4 space-y-4">
        {error && <div className="bg-yellow-50 text-yellow-800 text-sm rounded p-3">{error}</div>}
        {pdfError && <div className="bg-red-50 text-red-700 text-sm rounded p-3">{pdfError}</div>}
        {loading ? <p className="text-sm text-gray-500">Loading business overview…</p> : (
          <>
            <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <Metric label="Invoiced Sales" value={money(invoicedSales)} />
              <Metric label="Outstanding" value={money(outstanding)} />
              <Metric label="Stock Items" value={stockItems} />
              <Metric label="Posted Production Runs" value={postedRuns} />
            </section>

            <section className="bg-white rounded-xl shadow-sm p-4">
              <h2 className="font-semibold text-gray-700 mb-3">Monthly Invoiced Sales Trend</h2>
              <div className="space-y-3">
                {monthlySales.map(([month, total]) => (
                  <div key={month} className="grid grid-cols-[5rem_1fr_auto] items-center gap-3 text-sm">
                    <span className="text-gray-500">{month}</span>
                    <div className="h-3 bg-gray-100 rounded overflow-hidden"><div className="h-full bg-blue-600 rounded" style={{ width: `${(total / maxMonthlySales) * 100}%` }} /></div>
                    <span className="font-medium text-gray-700">{money(total)}</span>
                  </div>
                ))}
                {!monthlySales.length && <p className="text-sm text-gray-500">No invoiced sales available yet.</p>}
              </div>
            </section>

            <section className="bg-white rounded-xl shadow-sm p-4">
              <h2 className="font-semibold text-gray-700 mb-3">Business-wide Sales & Invoices</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-gray-500 border-b">
                    <th className="py-2 pr-3">Order</th><th className="py-2 pr-3">Customer</th><th className="py-2 pr-3">Salesman</th><th className="py-2 pr-3">Date</th><th className="py-2 pr-3">Status</th><th className="py-2 pr-3">Invoice</th><th className="py-2 pr-3">Paid</th><th className="py-2 pr-3">Outstanding</th><th className="py-2">PDF</th>
                  </tr></thead>
                  <tbody>{orders.slice(0, 15).map(order => (
                    <tr key={order.id} className="border-b last:border-0">
                      <td className="py-2 pr-3">{order.order_number}</td><td className="py-2 pr-3">{order.customer_name}</td><td className="py-2 pr-3">{order.salesman_name || '—'}</td><td className="py-2 pr-3">{order.order_date}</td><td className="py-2 pr-3 capitalize">{order.status}</td><td className="py-2 pr-3">{order.invoice_number || (order.invoice_total ? money(order.invoice_total) : '—')}</td><td className="py-2 pr-3">{money(order.amount_paid)}</td><td className="py-2 pr-3">{money(order.outstanding)}</td><td className="py-2">{order.invoice_number ? <button onClick={() => downloadInvoice(order)} className="text-blue-600 hover:underline">Download</button> : '—'}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </section>

            <section className="bg-white rounded-xl shadow-sm p-4">
              <h2 className="font-semibold text-gray-700 mb-3">Payment Register</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-gray-500 border-b"><th className="py-2 pr-3">Date</th><th className="py-2 pr-3">Order</th><th className="py-2 pr-3">Customer</th><th className="py-2 pr-3">Reference</th><th className="py-2">Amount</th></tr></thead>
                  <tbody>{payments.slice(0, 15).map(payment => <tr key={payment.payment_id} className="border-b last:border-0"><td className="py-2 pr-3">{payment.payment_date}</td><td className="py-2 pr-3">{payment.order_number}</td><td className="py-2 pr-3">{payment.customer_name}</td><td className="py-2 pr-3">{payment.reference || '—'}</td><td className="py-2">{money(payment.amount)}</td></tr>)}</tbody>
                </table>
              </div>
            </section>

            <section className="bg-white rounded-xl shadow-sm p-4">
              <h2 className="font-semibold text-gray-700 mb-3">Production Overview</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-gray-500 border-b"><th className="py-2 pr-3">Run Date</th><th className="py-2 pr-3">Finished Good</th><th className="py-2 pr-3">Planned</th><th className="py-2 pr-3">Actual</th><th className="py-2 pr-3">Damaged</th><th className="py-2">Status</th></tr></thead>
                  <tbody>{runs.slice(0, 15).map(run => <tr key={run.run_id} className="border-b last:border-0"><td className="py-2 pr-3">{run.run_date}</td><td className="py-2 pr-3">{run.finished_item_code} · {run.finished_item_name}</td><td className="py-2 pr-3">{run.planned_output}</td><td className="py-2 pr-3">{run.actual_output}</td><td className="py-2 pr-3">{run.damaged_qty}</td><td className="py-2 capitalize">{run.status}</td></tr>)}</tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  )
}

function Metric({ label, value }) {
  return <div className="bg-white rounded-xl shadow-sm p-4"><div className="text-xs text-gray-500">{label}</div><div className="text-xl font-semibold text-gray-800 mt-1">{value}</div></div>
}
