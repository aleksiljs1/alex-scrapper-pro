import StatusBadge from '../dashboard/StatusBadge'
import type { ProfileStatus } from '../../types/profile'
import { formatDate } from '../../utils/formatters'

interface QueueItemProps {
  id: string
  url: string
  status: ProfileStatus
  name: string | null
  updatedAt: string
}

export default function QueueItem({ url, status, name, updatedAt }: QueueItemProps) {
  const slug = url.split('/').pop() || url

  return (
    <div className="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-dark-surface rounded-lg">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{name || slug}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">{formatDate(updatedAt)}</p>
      </div>
      <StatusBadge status={status} />
    </div>
  )
}
