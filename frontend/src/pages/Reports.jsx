// frontend/src/pages/Reports.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

const REPORTS = [
  {
    label: 'Stock Ledger',
    endpoint: '/reports/stock',
    filename: 'stock_ledger.xlsx',
    description: 'All stock movements with running balance',
  },
  {
    label: 'Sales Register',
    endpoint: '/reports/sales',
    filename: 'sales_register.xlsx',
    description: 'Customer-wise and product-wise sales with GST breakup',
  },
  {
    label: 'Purchase Register',
    endpoint: '/reports/purchases',
    filename: 'purchase_register.xlsx',
    description: 'All purchases by supplier and item',
  },
  {
    label: 'Production Costing',
    endpoint: '/reports/production-costing',
    filename: 'production_costing.xlsx',
    description: 'Planned vs actual consumption, yield variance, cost per packet',
  },
  {
    label: 'GST Summary',
    endpoint: '/reports/gst-summary',
    filename: 'gst_summary.xlsx',
    description: 'Outward supplies summary mapping to GSTR-1 / GSTR-3B',
  },
  {
    label: 'Outstanding & Ageing',
    endpoint: '/reports/outstanding-ageing',
    filename: 'outstanding_ageing.xlsx',
    description: 'Customer-wise receivables with ageing buckets',
  },
]

export default function Reports() {
  const navigate = useNavigate()
  const name = localStorage.getItem('name')
  const role = localStorage.getItem('role')
  const [downloading, setDownloading] = useState(null)
  const [error, setError] = useState(null)
  const visibleReports = role === 'production'
    ? REPORTS.filter(report => ['/reports/stock'].includes(report.endpoint))
    : REPORTS

  async function handleDownload(report) {
    setError(null)
    setDownloading(report.endpoint)
    try {
      const res = await api.get(report.endpoint, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = report.filename
      a.click()
      window.URL.revokeObjectURL(url)
    } catch {
      setError(`Failed to download ${report.label}`)
    } finally {
      setDownloading(null)
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
          <div className="font-bold text-lg">CDI Food ERP — Reports</div>
          <div className="text-gray-400 text-xs">{name}</div>
        </div>
        <div className="flex gap-2">
          {role === 'admin' && (
            <button onClick={() => navigate('/admin')}
              className="bg-gray-700 text-xs px-3 py-1 rounded">Admin</button>
          )}
          <button onClick={() => navigate('/inventory')}
            className="bg-gray-700 text-xs px-3 py-1 rounded">Inventory</button>
          {(role === 'admin' || role === 'production') && (
            <button onClick={() => navigate('/production')}
              className="bg-gray-700 text-xs px-3 py-1 rounded">Production</button>
          )}
          <button onClick={logout}
            className="bg-gray-700 text-xs px-3 py-1 rounded">Logout</button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto p-4 space-y-4">

        {error && <div className="bg-red-50 text-red-600 text-sm rounded p-3">{error}</div>}

        <div className="bg-white rounded-xl shadow-sm p-4">
          <h2 className="font-semibold text-gray-700 mb-4">Export Reports</h2>
          <div className="space-y-3">
            {visibleReports.map(report => (
              <div key={report.endpoint}
                className="flex items-center justify-between border rounded-lg p-3">
                <div>
                  <div className="font-medium text-sm text-gray-800">{report.label}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{report.description}</div>
                </div>
                <button
                  onClick={() => handleDownload(report)}
                  disabled={downloading === report.endpoint}
                  className="bg-blue-600 text-white text-xs px-3 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap ml-4">
                  {downloading === report.endpoint ? 'Downloading...' : 'Download Excel'}
                </button>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
