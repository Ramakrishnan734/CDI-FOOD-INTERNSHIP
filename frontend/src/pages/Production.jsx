// frontend/src/pages/Production.jsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

export default function Production() {
  const navigate = useNavigate()
  const name = localStorage.getItem('name')
  const role = localStorage.getItem('role')

  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)
  const [draftRun, setDraftRun] = useState(null)

  // Start run form
  const [startForm, setStartForm] = useState({
    fg_item_code: 'FG-MRK200',
    batch_size: 1,
    run_date: new Date().toISOString().split('T')[0],
    notes: '',
    labour_cost: '',
    overhead_cost: '',
  })

  // Post run form
  const [postForm, setPostForm] = useState({
    actual_output: '',
    actual_lines: [],
  })

  function logout() {
    localStorage.clear()
    navigate('/login')
  }

  async function handleStart(e) {
  e.preventDefault()
  setMessage(null)
  setError(null)

  try {
    const batches = parseInt(startForm.batch_size, 10)

    const res = await api.post('/production/start', {
      bom_id: 1,
      planned_output: batches * 200,
      run_date: startForm.run_date,
      labour_cost: parseFloat(startForm.labour_cost || 0),
      overhead_cost: parseFloat(startForm.overhead_cost || 0),
    })

    setDraftRun(res.data)

    setPostForm(p => ({
      ...p,
      actual_lines: res.data.planned_lines.map(l => ({
        item_code: l.item_code,
        planned_qty: l.planned_qty,
        actual_qty: String(l.planned_qty),
      })),
    }))

    setMessage(
      `Draft run created. Run ID: ${res.data.run_id}. Now enter actual output below.`
    )
  } catch (err) {
    setError(err.response?.data?.detail || 'Failed to start production run')
  }
}

  async function handlePost(e) {
    e.preventDefault()
    setMessage(null); setError(null)
    try {
      const payload = {
        actual_output: parseInt(postForm.actual_output),
        actual_lines: postForm.actual_lines.map(l => ({
          item_code: l.item_code,
          actual_qty: parseFloat(l.actual_qty),
        })),
      }
      const res = await api.post(`/production/${draftRun.run_id}/post`, payload)
      setMessage(
        `Run posted! Output: ${res.data.actual_output} packets. ` +
        `Cost per packet: ₹${res.data.cost_per_packet}.`
      )
      setDraftRun(null)
      setPostForm({ actual_output: '', actual_lines: [] })
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to post production run')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-gray-800 text-white px-4 py-3 flex justify-between items-center">
        <div>
          <div className="font-bold text-lg">CDI Food ERP — Production</div>
          <div className="text-gray-400 text-xs">{name}</div>
        </div>
        <div className="flex gap-2">
          {role === 'admin' && (
            <button onClick={() => navigate('/admin')}
              className="bg-gray-700 text-xs px-3 py-1 rounded">Admin</button>
          )}
          <button onClick={() => navigate('/inventory')}
            className="bg-gray-700 text-xs px-3 py-1 rounded">Inventory</button>
          <button onClick={() => navigate('/reports')}
            className="bg-gray-700 text-xs px-3 py-1 rounded">Reports</button>
          <button onClick={logout}
            className="bg-gray-700 text-xs px-3 py-1 rounded">Logout</button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto p-4 space-y-4">

        {message && <div className="bg-green-50 text-green-700 text-sm rounded p-3">{message}</div>}
        {error && <div className="bg-red-50 text-red-600 text-sm rounded p-3">{error}</div>}

        {/* Step 1 — Start a production run */}
        {!draftRun && (
          <div className="bg-white rounded-xl shadow-sm p-4">
            <h2 className="font-semibold text-gray-700 mb-1">Step 1 — Start Production Run</h2>
            <p className="text-xs text-gray-400 mb-3">
              This creates a draft run and shows planned material consumption from the BOM.
            </p>

            <form onSubmit={handleStart} className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500">Finished Good Item Code</label>
                <input
                  value={startForm.fg_item_code}
                  onChange={e => setStartForm(p => ({ ...p, fg_item_code: e.target.value }))}
                  required
                  className="w-full border rounded px-2 py-1 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Number of Batches</label>
                <input
                  type="number" min="1"
                  value={startForm.batch_size}
                  onChange={e => setStartForm(p => ({ ...p, batch_size: e.target.value }))}
                  required
                  className="w-full border rounded px-2 py-1 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Run Date</label>
                <input
                  type="date"
                  value={startForm.run_date}
                  onChange={e => setStartForm(p => ({ ...p, run_date: e.target.value }))}
                  required
                  className="w-full border rounded px-2 py-1 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Labour Cost (₹)</label>
                <input
                  type="number" step="0.01" min="0"
                  value={startForm.labour_cost}
                  onChange={e => setStartForm(p => ({ ...p, labour_cost: e.target.value }))}
                  placeholder="e.g. 1200"
                  className="w-full border rounded px-2 py-1 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Power/Gas Cost (₹)</label>
                <input
                  type="number" step="0.01" min="0"
                  value={startForm.overhead_cost}
                  onChange={e => setStartForm(p => ({ ...p, overhead_cost: e.target.value }))}
                  placeholder="e.g. 600"
                  className="w-full border rounded px-2 py-1 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Notes (optional)</label>
                <input
                  value={startForm.notes}
                  onChange={e => setStartForm(p => ({ ...p, notes: e.target.value }))}
                  className="w-full border rounded px-2 py-1 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div className="col-span-2">
                <button type="submit"
                  className="bg-blue-600 text-white text-sm px-4 py-2 rounded hover:bg-blue-700">
                  Start Run
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Step 2 — Post actual output */}
        {draftRun && (
          <div className="bg-white rounded-xl shadow-sm p-4">
            <h2 className="font-semibold text-gray-700 mb-1">
              Step 2 — Post Actual Output (Run ID: {draftRun.run_id})
            </h2>
            <p className="text-xs text-gray-400 mb-3">
              Planned output: {draftRun.planned_output} packets. Enter actual quantities below.
            </p>

            <form onSubmit={handlePost} className="space-y-4">

              {/* Actual material consumption */}
              <div>
                <h3 className="text-sm font-medium text-gray-600 mb-2">Actual Material Consumption</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="pb-2 pr-4">Item</th>
                      <th className="pb-2 pr-4">Planned Qty</th>
                      <th className="pb-2">Actual Qty</th>
                    </tr>
                  </thead>
                  <tbody>
                    {postForm.actual_lines.map((line, i) => (
                      <tr key={line.item_code} className="border-b last:border-0">
                        <td className="py-2 pr-4 font-mono text-xs">{line.item_code}</td>
                        <td className="py-2 pr-4 text-gray-500">{line.planned_qty}</td>
                        <td className="py-2">
                          <input
                            type="number" step="0.001"
                            value={line.actual_qty}
                            onChange={e => {
                              const lines = [...postForm.actual_lines]
                              lines[i] = { ...lines[i], actual_qty: e.target.value }
                              setPostForm(p => ({ ...p, actual_lines: lines }))
                            }}
                            required
                            className="border rounded px-2 py-1 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-blue-400"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Actual output */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500">Actual Output (packets)</label>
                  <input
                    type="number" min="0"
                    value={postForm.actual_output}
                    onChange={e => setPostForm(p => ({ ...p, actual_output: e.target.value }))}
                    required placeholder="e.g. 188"
                    className="w-full border rounded px-2 py-1 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                </div>
              </div>

              <div className="flex gap-3">
                <button type="submit"
                  className="bg-green-600 text-white text-sm px-4 py-2 rounded hover:bg-green-700">
                  Post Run
                </button>
                <button type="button" onClick={() => setDraftRun(null)}
                  className="text-sm text-gray-500 hover:underline">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

      </div>
    </div>
  )
}
