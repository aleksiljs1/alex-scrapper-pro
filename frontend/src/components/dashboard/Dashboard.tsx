import { useState, useEffect, useMemo } from 'react'
import { useProfiles } from '../../hooks/useProfiles'
import ProfileCard from './ProfileCard'
import FilterBar, { type Filters } from './FilterBar'
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'

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

export default function Dashboard() {
  const [filters, setFilters] = useState<Filters>(emptyFilters)
  const [debounced, setDebounced] = useState<Filters>(emptyFilters)
  const [page, setPage] = useState(1)

  // Debounce all text filter values (300ms), status changes immediately
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(filters), 300)
    return () => clearTimeout(timer)
  }, [filters])

  // Reset page when any filter changes
  useEffect(() => {
    setPage(1)
  }, [debounced])

  // Build query params — only include non-empty values
  const queryParams = useMemo(() => ({
    status: debounced.status || undefined,
    search: debounced.search || undefined,
    keywords: debounced.keywords || undefined,
    district: debounced.district || undefined,
    division: debounced.division || undefined,
    upazila: debounced.upazila || undefined,
    country: debounced.country || undefined,
    college: debounced.college || undefined,
    high_school: debounced.high_school || undefined,
    page,
    limit: 20,
  }), [debounced, page])

  const { data, isLoading, isError, isFetching } = useProfiles(queryParams)

  return (
    <div>
      <FilterBar
        filters={filters}
        onChange={setFilters}
      />

      {isLoading && !data ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="animate-spin text-blue-500" size={32} />
        </div>
      ) : isError ? (
        <div className="text-center py-12">
          <p className="text-red-500 dark:text-red-400">Failed to load profiles. Make sure the backend is running.</p>
        </div>
      ) : data?.items.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 dark:text-gray-400">No profiles found. Add one to get started!</p>
        </div>
      ) : (
        <>
          {/* Subtle refetch indicator */}
          {isFetching && (
            <div className="flex items-center gap-2 mb-3 text-xs text-gray-400">
              <Loader2 className="animate-spin" size={12} />
              Updating...
            </div>
          )}

          <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 transition-opacity ${isFetching ? 'opacity-70' : ''}`}>
            {data?.items.map((profile) => (
              <ProfileCard key={profile.id} profile={profile} />
            ))}
          </div>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-center gap-4 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 dark:border-dark-border rounded-lg disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-dark-surface text-gray-700 dark:text-gray-300"
              >
                <ChevronLeft size={16} />
                Prev
              </button>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Page {data.page} of {data.pages} ({data.total} total)
              </span>
              <button
                onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                disabled={page >= data.pages}
                className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 dark:border-dark-border rounded-lg disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-dark-surface text-gray-700 dark:text-gray-300"
              >
                Next
                <ChevronRight size={16} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
