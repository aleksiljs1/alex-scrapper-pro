import { Activity } from 'lucide-react'
import { useQueueStatus } from '../../hooks/useProfiles'

export default function QueuePanel() {
  const { data } = useQueueStatus()

  if (!data) return null

  const total = data.queued + data.processing + data.finished + data.failed

  return (
    <div className="bg-white dark:bg-dark-card rounded-xl border border-gray-200 dark:border-dark-border p-5">
      <div className="flex items-center gap-2 mb-4">
        <Activity size={16} className="text-gray-500 dark:text-gray-400" />
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 text-sm">Queue Overview</h3>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Total" value={total} color="gray" />
        <StatCard label="Queued" value={data.queued} color="yellow" />
        <StatCard label="Processing" value={data.processing} color="blue" />
        <StatCard label="Finished" value={data.finished} color="green" />
        <StatCard label="Failed" value={data.failed} color="red" />
      </div>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colorMap: Record<string, string> = {
    gray: 'bg-gray-50 text-gray-700 dark:bg-gray-800/50 dark:text-gray-300',
    yellow: 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-300',
    blue: 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300',
    green: 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300',
    red: 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300',
  }

  return (
    <div className={`${colorMap[color] || colorMap.gray} rounded-lg p-3 text-center`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs mt-0.5">{label}</p>
    </div>
  )
}
