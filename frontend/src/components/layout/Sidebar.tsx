import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, PlusCircle, Activity } from 'lucide-react'
import { useQueueStatus } from '../../hooks/useProfiles'

export default function Sidebar() {
  const { pathname } = useLocation()
  const { data: queueStatus } = useQueueStatus()

  const links = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/add', label: 'Add Profile', icon: PlusCircle },
  ]

  return (
    <aside className="w-64 bg-white dark:bg-dark-card border-r border-gray-200 dark:border-dark-border flex flex-col min-h-screen">
      <div className="p-4 border-b border-gray-200 dark:border-dark-border">
        <h1 className="text-lg font-bold text-blue-600 dark:text-blue-400">FB Scraper</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400">Profile Scraper Dashboard</p>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
              pathname === to
                ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-dark-surface hover:text-gray-900 dark:hover:text-gray-200'
            }`}
          >
            <Icon size={18} />
            <span>{label}</span>
          </Link>
        ))}
      </nav>

      {queueStatus && (
        <div className="p-4 border-t border-gray-200 dark:border-dark-border">
          <div className="flex items-center gap-2 mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
            <Activity size={16} />
            <span>Queue Status</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded px-2 py-1">
              <span className="text-yellow-700 dark:text-yellow-400 font-medium">{queueStatus.queued}</span>
              <span className="text-yellow-600 dark:text-yellow-500 ml-1">Queued</span>
            </div>
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded px-2 py-1">
              <span className="text-blue-700 dark:text-blue-400 font-medium">{queueStatus.processing}</span>
              <span className="text-blue-600 dark:text-blue-500 ml-1">Active</span>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 rounded px-2 py-1">
              <span className="text-green-700 dark:text-green-400 font-medium">{queueStatus.finished}</span>
              <span className="text-green-600 dark:text-green-500 ml-1">Done</span>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 rounded px-2 py-1">
              <span className="text-red-700 dark:text-red-400 font-medium">{queueStatus.failed}</span>
              <span className="text-red-600 dark:text-red-500 ml-1">Failed</span>
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
