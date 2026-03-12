import type { LucideIcon } from 'lucide-react'
import type { ProfileData } from '../../types/profile'
import { formatLocation, formatCount } from '../../utils/formatters'
import {
  User, MapPin, Home, Briefcase, GraduationCap, Heart,
  Users, Globe, Calendar, Tag, MessageSquare
} from 'lucide-react'

export default function ProfileDetail({ profile }: { profile: ProfileData }) {
  return (
    <div className="space-y-6">
      {/* Header with cover + avatar */}
      <div className="bg-white dark:bg-dark-card rounded-xl border border-gray-200 dark:border-dark-border overflow-hidden">
        {profile.cover_photo_url && (
          <div className="h-48 bg-gray-200 dark:bg-dark-surface">
            <img
              src={profile.cover_photo_url}
              alt="Cover"
              className="w-full h-full object-cover"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
            />
          </div>
        )}
        <div className="p-6">
          <div className="flex items-start gap-4">
            {profile.profile_picture_url ? (
              <img
                src={profile.profile_picture_url}
                alt={profile.name || ''}
                className="w-20 h-20 rounded-full object-cover border-4 border-white dark:border-dark-card shadow -mt-14"
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-gray-200 dark:bg-dark-surface flex items-center justify-center border-4 border-white dark:border-dark-card shadow -mt-14">
                <User size={32} className="text-gray-400 dark:text-gray-500" />
              </div>
            )}
            <div className="flex-1 pt-1">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{profile.name || 'Unknown'}</h1>
              {profile.bio && (
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 whitespace-pre-line">{profile.bio}</p>
              )}
              {profile.category && (
                <span className="inline-flex items-center gap-1 mt-2 px-2 py-0.5 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full text-xs">
                  <Tag size={12} /> {profile.category}
                </span>
              )}
            </div>
          </div>

          {/* Counts */}
          <div className="flex gap-6 mt-4 pt-4 border-t border-gray-100 dark:border-dark-border">
            {profile.friends_count !== null && (
              <div className="text-sm">
                <span className="font-semibold text-gray-900 dark:text-gray-100">{formatCount(profile.friends_count)}</span>
                <span className="text-gray-500 dark:text-gray-400 ml-1">Friends</span>
              </div>
            )}
            {profile.followers_count !== null && (
              <div className="text-sm">
                <span className="font-semibold text-gray-900 dark:text-gray-100">{formatCount(profile.followers_count)}</span>
                <span className="text-gray-500 dark:text-gray-400 ml-1">Followers</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Intro Items */}
        {profile.intro_items.length > 0 && (
          <Section title="Intro" icon={MessageSquare}>
            <ul className="space-y-2">
              {profile.intro_items.map((item, i) => (
                <li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-start gap-2">
                  <span className="text-gray-400 dark:text-gray-500 mt-0.5">•</span>
                  {item}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {/* Location */}
        {(profile.current_city || profile.hometown) && (
          <Section title="Location" icon={MapPin}>
            <div className="space-y-3">
              {profile.current_city && (
                <InfoRow icon={MapPin} label="Current city" value={formatLocation(profile.current_city)} />
              )}
              {profile.hometown && (
                <InfoRow icon={Home} label="Hometown" value={formatLocation(profile.hometown)} />
              )}
            </div>
          </Section>
        )}

        {/* Work */}
        {profile.work.length > 0 && (
          <Section title="Work" icon={Briefcase}>
            <div className="space-y-3">
              {profile.work.map((w, i) => (
                <div key={i} className="border-l-2 border-blue-200 dark:border-blue-700 pl-3">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {w.designation && <span>{w.designation}</span>}
                    {w.designation && w.organization && <span className="text-gray-500 dark:text-gray-400"> at </span>}
                    {w.organization && <span className="text-blue-600 dark:text-blue-400">{w.organization}</span>}
                  </p>
                  {w.details.map((d, j) => (
                    <p key={j} className="text-xs text-gray-500 dark:text-gray-400">{d}</p>
                  ))}
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Education */}
        {profile.education.length > 0 && (
          <Section title="Education" icon={GraduationCap}>
            <div className="space-y-3">
              {profile.education.map((e, i) => (
                <div key={i} className="border-l-2 border-green-200 dark:border-green-700 pl-3">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{e.institution}</p>
                  {e.type && <p className="text-xs text-gray-500 dark:text-gray-400">{e.type}</p>}
                  {e.field_of_study && <p className="text-xs text-gray-600 dark:text-gray-400">Field: {e.field_of_study}</p>}
                  {e.details.map((d, j) => (
                    <p key={j} className="text-xs text-gray-500 dark:text-gray-400">{d}</p>
                  ))}
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Relationship */}
        {profile.relationship.length > 0 && (
          <Section title="Relationship" icon={Heart}>
            <div className="space-y-2">
              {profile.relationship.map((r, i) => (
                <div key={i}>
                  <p className="text-sm text-gray-700 dark:text-gray-300">{r.status}</p>
                  {r.partner_info?.name && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Partner: {r.partner_info.name}
                      {r.partner_info.profile_url && (
                        <a href={r.partner_info.profile_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 dark:text-blue-400 ml-1">
                          (profile)
                        </a>
                      )}
                    </p>
                  )}
                  {r.details.map((d, j) => (
                    <p key={j} className="text-xs text-gray-500 dark:text-gray-400">{d}</p>
                  ))}
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Family */}
        {profile.family_members.length > 0 && (
          <Section title="Family" icon={Users}>
            <div className="space-y-2">
              {profile.family_members.map((f, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div>
                    <p className="text-sm text-gray-700 dark:text-gray-300">{f.name}</p>
                    {f.relationship && <p className="text-xs text-gray-500 dark:text-gray-400">{f.relationship}</p>}
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Birthday */}
        {profile.birthday_info?.birthday && (
          <Section title="Birthday" icon={Calendar}>
            <p className="text-sm text-gray-700 dark:text-gray-300">{profile.birthday_info.birthday}</p>
          </Section>
        )}

        {/* Languages */}
        {profile.language_skills.length > 0 && (
          <Section title="Languages" icon={Globe}>
            <div className="flex flex-wrap gap-2">
              {profile.language_skills.map((lang, i) => (
                <span key={i} className="px-2 py-1 bg-gray-100 dark:bg-dark-surface rounded text-xs text-gray-700 dark:text-gray-300">
                  {lang}
                </span>
              ))}
            </div>
          </Section>
        )}

        {/* Names / Nicknames */}
        {profile.names && (profile.names.nicknames.length > 0 || profile.names.name_pronunciation) && (
          <Section title="Other Names" icon={User}>
            {profile.names.nicknames.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {profile.names.nicknames.map((n, i) => (
                  <span key={i} className="px-2 py-1 bg-blue-50 dark:bg-blue-900/30 rounded text-xs text-blue-700 dark:text-blue-300">{n}</span>
                ))}
              </div>
            )}
            {profile.names.name_pronunciation && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Pronunciation: {profile.names.name_pronunciation}</p>
            )}
          </Section>
        )}

        {/* Gender */}
        {profile.gender && (
          <Section title="Gender" icon={User}>
            <p className="text-sm text-gray-700 dark:text-gray-300">{profile.gender}</p>
          </Section>
        )}
      </div>
    </div>
  )
}

function Section({ title, icon: Icon, children }: { title: string; icon: LucideIcon; children: React.ReactNode }) {
  return (
    <div className="bg-white dark:bg-dark-card rounded-xl border border-gray-200 dark:border-dark-border p-5">
      <div className="flex items-center gap-2 mb-3">
        <Icon size={16} className="text-gray-500 dark:text-gray-400" />
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 text-sm">{title}</h3>
      </div>
      {children}
    </div>
  )
}

function InfoRow({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <Icon size={14} className="text-gray-400 dark:text-gray-500 mt-0.5" />
      <div>
        <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
        <p className="text-sm text-gray-700 dark:text-gray-300">{value}</p>
      </div>
    </div>
  )
}
