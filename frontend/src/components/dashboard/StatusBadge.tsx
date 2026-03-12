import type { ProfileStatus } from '../../types/profile'

const statusConfig: Record<ProfileStatus, { label: string; classes: string }> = {
  queued: {
    label: 'Queued',
    classes: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-700',
  },
  processing: {
    label: 'Processing',
    classes: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-700',
  },
  finished: {
    label: 'Finished',
    classes: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700',
  },
  failed: {
    label: 'Failed',
    classes: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700',
  },
}

export default function StatusBadge({ status }: { status: ProfileStatus }) {
  const config = statusConfig[status] || statusConfig.queued

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.classes}`}
    >
      {status === 'processing' && (
        <span className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-1.5 animate-pulse" />
      )}
      {config.label}
    </span>
  )
}
