import Dashboard from '../components/dashboard/Dashboard'
import QueuePanel from '../components/queue/QueuePanel'

export default function DashboardPage() {
  return (
    <div className="flex gap-6">
      <div className="flex-1 min-w-0">
        <Dashboard />
      </div>
      <div className="hidden xl:block w-72 flex-shrink-0">
        <QueuePanel />
      </div>
    </div>
  )
}
