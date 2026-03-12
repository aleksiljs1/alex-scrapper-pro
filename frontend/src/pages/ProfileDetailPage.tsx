import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2, AlertTriangle } from 'lucide-react'
import { useProfile } from '../hooks/useProfiles'
import ProfileDetail from '../components/profile/ProfileDetail'
import AboutTabsView from '../components/profile/AboutTabsView'
import StatusBadge from '../components/dashboard/StatusBadge'
import type { ProfileDocument } from '../types/profile'

export default function ProfileDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: doc, isLoading, isError } = useProfile(id!) as {
    data: ProfileDocument | undefined
    isLoading: boolean
    isError: boolean
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 size={32} className="animate-spin text-blue-500" />
      </div>
    )
  }

  if (isError || !doc) {
    return (
      <div className="flex flex-col items-center justify-center py-32 gap-3">
        <AlertTriangle size={40} className="text-red-400" />
        <p className="text-gray-600 dark:text-gray-400">Profile not found or failed to load.</p>
        <button
          onClick={() => navigate('/')}
          className="text-blue-600 dark:text-blue-400 hover:underline text-sm"
        >
          Back to Dashboard
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
      >
        <ArrowLeft size={16} />
        Back
      </button>

      {/* Status bar */}
      <div className="flex items-center gap-3 bg-white dark:bg-dark-card rounded-xl border border-gray-200 dark:border-dark-border px-5 py-3">
        <StatusBadge status={doc.status} />
        <span className="text-sm text-gray-500 dark:text-gray-400">
          URL: <a href={doc.url} target="_blank" rel="noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">{doc.url}</a>
        </span>
        {doc.error_message && (
          <span className="text-sm text-red-500 dark:text-red-400 ml-auto">{doc.error_message}</span>
        )}
      </div>

      {doc.profile ? (
        <ProfileDetail profile={doc.profile} />
      ) : (
        <div className="bg-white dark:bg-dark-card rounded-xl border border-gray-200 dark:border-dark-border p-8 text-center text-gray-500 dark:text-gray-400">
          Profile data not yet available. Current status: <strong>{doc.status}</strong>.
        </div>
      )}

      {doc.scraped_data?.about_tabs && doc.scraped_data.about_tabs.length > 0 && (
        <AboutTabsView tabs={doc.scraped_data.about_tabs} />
      )}
    </div>
  )
}
