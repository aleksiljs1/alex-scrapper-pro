import { format, parseISO } from 'date-fns'

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  try {
    return format(parseISO(dateStr), 'MMM d, yyyy h:mm a')
  } catch {
    return dateStr
  }
}

export function formatCount(count: number | null | undefined): string {
  if (count === null || count === undefined) return '—'
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`
  return count.toString()
}

export function formatLocation(loc: {
  upazila?: string | null
  district?: string | null
  division?: string | null
  country?: string | null
} | null): string {
  if (!loc) return '—'
  const parts = [loc.upazila, loc.district, loc.division, loc.country].filter(Boolean)
  return parts.join(', ') || '—'
}
