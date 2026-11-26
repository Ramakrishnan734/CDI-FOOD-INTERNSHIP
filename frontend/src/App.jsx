// frontend/src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import SalesmanDashboard from './pages/SalesmanDashboard'
import AdminDashboard from './pages/AdminDashboard'
import Inventory from './pages/Inventory'
import Production from './pages/Production'
import Reports from './pages/Reports'
import RoleDashboard from './pages/RoleDashboard'

function PrivateRoute({ children, roles }) {
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('role')
  if (!token) return <Navigate to="/login" replace />
  if (roles && !roles.includes(role)) return <Navigate to={roleHome(role)} replace />
  return children
}

function roleHome(role) {
  if (role === 'admin') return '/admin'
  if (role === 'production') return '/production'
  if (role === 'auditor') return '/accountant'
  if (role === 'owner') return '/owner'
  return '/salesman'
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/salesman" element={<PrivateRoute roles={['salesman', 'admin']}><SalesmanDashboard /></PrivateRoute>} />
        <Route path="/admin" element={<PrivateRoute roles={['admin']}><AdminDashboard /></PrivateRoute>} />
        <Route path="/owner" element={<PrivateRoute roles={['owner']}><RoleDashboard role="owner" /></PrivateRoute>} />
        <Route path="/accountant" element={<PrivateRoute roles={['auditor']}><RoleDashboard role="auditor" /></PrivateRoute>} />
        <Route path="/inventory" element={<PrivateRoute roles={['admin', 'production', 'auditor', 'owner']}><Inventory /></PrivateRoute>} />
        <Route path="/production" element={<PrivateRoute roles={['admin', 'production']}><Production /></PrivateRoute>} />
        <Route path="/reports" element={<PrivateRoute roles={['admin', 'production', 'auditor', 'owner']}><Reports /></PrivateRoute>} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
