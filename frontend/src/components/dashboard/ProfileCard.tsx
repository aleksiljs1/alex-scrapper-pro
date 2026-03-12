import { useNavigate } from 'react-router-dom'
import { Trash2, User, MapPin, Briefcase } from 'lucide-react'
import StatusBadge from './StatusBadge'
import { useDeleteProfile } from '../../hooks/useProfiles'
import { formatDate } from '../../utils/formatters'
import type { ProfileDocument } from '../../types/profile'

export default function ProfileCard({ profile }: { profile: ProfileDocument }) {
  const navigate = useNavigate()
  const deleteMutation = useDeleteProfile()

  const p = profile.profile
  const name = p?.name || profile.url_slug || 'Unknown'
  const city = p?.current_city
    ? typeof p.current_city === 'object'
      ? [p.current_city.district, p.current_city.country].filter(Boolean).join(', ')
      : String(p.current_city)
    : null

  const firstWork = p?.work?.[0]
  const workText = firstWork
    ? typeof firstWork === 'object'
      ? [firstWork.designation, firstWork.organization].filter(Boolean).join(' at ')
      : String(firstWork)
    : null

  return (
    <div
      className="bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border rounded-xl p-4 hover:shadow-md dark:hover:shadow-dark-border/20 transition-shadow cursor-pointer"
      onClick={() => navigate(`/profiles/${profile.id}`)}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          {p?.profile_picture_url ? (
            <img
              src={p.profile_picture_url}
              alt={name}
              className="w-12 h-12 rounded-full object-cover bg-gray-100"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none'
              }}
            />
          ) : (
            <div className="w-12 h-12 rounded-full bg-gray-200 dark:bg-dark-surface flex items-center justify-center">
              <User size={20} className="text-gray-400 dark:text-gray-500" />
            </div>
          )}
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-sm">{name}</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[200px]">{profile.url_slug}</p>
          </div>
        </div>
        <StatusBadge status={profile.status} />
      </div>

      {(city || workText) && (
        <div className="space-y-1 mb-3">
          {city && (
            <div className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
              <MapPin size={12} />
              <span>{city}</span>
            </div>
          )}
          {workText && (
            <div className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
              <Briefcase size={12} />
              <span className="truncate">{workText}</span>
            </div>
          )}
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-gray-400 dark:text-gray-500">
        <span>{formatDate(profile.created_at)}</span>
        <button
          onClick={(e) => {
            e.stopPropagation()
            if (confirm('Delete this profile?')) {
              deleteMutation.mutate(profile.id)
            }
          }}
          className="p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 transition-colors"
          title="Delete"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  )
}
