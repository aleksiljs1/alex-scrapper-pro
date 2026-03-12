import { useState } from 'react'
import { Search, Filter, ChevronDown, ChevronUp, X } from 'lucide-react'

export interface Filters {
  status: string
  search: string
  keywords: string
  district: string
  division: string
  upazila: string
  country: string
  college: string
  high_school: string
}

interface FilterBarProps {
  filters: Filters
  onChange: (filters: Filters) => void
}

const statuses: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'queued', label: 'Queued' },
  { value: 'processing', label: 'Processing' },
  { value: 'finished', label: 'Finished' },
  { value: 'failed', label: 'Failed' },
]

const emptyFilters: Filters = {
  status: '',
  search: '',
  keywords: '',
  district: '',
  division: '',
  upazila: '',
  country: '',
  college: '',
  high_school: '',
}

export default function FilterBar({ filters, onChange }: FilterBarProps) {
  const [expanded, setExpanded] = useState(false)

  const set = (key: keyof Filters, value: string) =>
    onChange({ ...filters, [key]: value })

  const activeCount = Object.entries(filters).filter(
    ([k, v]) => v && k !== 'search' && k !== 'status'
  ).length

  const clearAll = () => onChange({ ...emptyFilters })

  return (
    <div className="mb-6 space-y-3">
      {/* Primary row — search + status */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            placeholder="Search by name or URL..."
            value={filters.search}
            onChange={(e) => set('search', e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-dark-border rounded-lg text-sm bg-white dark:bg-dark-card dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400 dark:placeholder-gray-500"
          />
        </div>
        <div className="relative">
          <Filter size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <select
            value={filters.status}
            onChange={(e) => set('status', e.target.value)}
            className="pl-10 pr-8 py-2 border border-gray-300 dark:border-dark-border rounded-lg text-sm bg-white dark:bg-dark-card dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none"
          >
            {statuses.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm border rounded-lg transition-colors ${
            activeCount > 0
              ? 'border-blue-400 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
              : 'border-gray-300 dark:border-dark-border text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-dark-surface'
          }`}
        >
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          Filters
          {activeCount > 0 && (
            <span className="ml-1 bg-blue-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {activeCount}
            </span>
          )}
        </button>
        {activeCount > 0 && (
          <button
            type="button"
            onClick={clearAll}
            className="inline-flex items-center gap-1 px-3 py-2 text-sm text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"
          >
            <X size={14} />
            Clear all
          </button>
        )}
      </div>

      {/* Expandable advanced filters */}
      {expanded && (
        <div className="bg-gray-50 dark:bg-dark-surface border border-gray-200 dark:border-dark-border rounded-xl p-4 space-y-4">
          {/* Keywords */}
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Keywords <span className="text-gray-400 dark:text-gray-500">(comma-separated, searches across all fields)</span>
            </label>
            <input
              type="text"
              placeholder="e.g. engineer, dhaka, google"
              value={filters.keywords}
              onChange={(e) => set('keywords', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-dark-border rounded-lg text-sm bg-white dark:bg-dark-card dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400 dark:placeholder-gray-500"
            />
          </div>

          {/* Location row */}
          <div>
            <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">Location</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <FilterInput label="Upazila" value={filters.upazila} onChange={(v) => set('upazila', v)} placeholder="e.g. Mirpur" />
              <FilterInput label="District" value={filters.district} onChange={(v) => set('district', v)} placeholder="e.g. Dhaka" />
              <FilterInput label="Division" value={filters.division} onChange={(v) => set('division', v)} placeholder="e.g. Dhaka" />
              <FilterInput label="Country" value={filters.country} onChange={(v) => set('country', v)} placeholder="e.g. Bangladesh" />
            </div>
          </div>

          {/* Education row */}
          <div>
            <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">Education</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <FilterInput label="College / University" value={filters.college} onChange={(v) => set('college', v)} placeholder="e.g. BUET" />
              <FilterInput label="High School" value={filters.high_school} onChange={(v) => set('high_school', v)} placeholder="e.g. Ideal School" />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function FilterInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder: string
}) {
  return (
    <div>
      <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</label>
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-1.5 border border-gray-300 dark:border-dark-border rounded-lg text-sm bg-white dark:bg-dark-card dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400 dark:placeholder-gray-500"
      />
    </div>
  )
}
