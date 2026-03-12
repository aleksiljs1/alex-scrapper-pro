import { Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import DashboardPage from './pages/DashboardPage'
import AddProfilePage from './pages/AddProfilePage'
import ProfileDetailPage from './pages/ProfileDetailPage'
import { useQueueWebSocket } from './hooks/useWebSocket'

function App() {
  useQueueWebSocket()

  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="add" element={<AddProfilePage />} />
        <Route path="profiles/:id" element={<ProfileDetailPage />} />
      </Route>
    </Routes>
  )
}

export default App
