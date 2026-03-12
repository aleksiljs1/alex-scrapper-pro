import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { getProfiles, getProfileById, addProfile, deleteProfile, getQueueStatus } from '../api/profiles'
import toast from 'react-hot-toast'

export function useProfiles(params: {
  status?: string
  search?: string
  keywords?: string
  district?: string
  division?: string
  upazila?: string
  country?: string
  college?: string
  high_school?: string
  page?: number
  limit?: number
}) {
  return useQuery({
    queryKey: ['profiles', params],
    queryFn: () => getProfiles(params),
    placeholderData: keepPreviousData,
  })
}

export function useProfile(id: string) {
  return useQuery({
    queryKey: ['profile', id],
    queryFn: () => getProfileById(id),
    enabled: !!id,
  })
}

export function useQueueStatus() {
  return useQuery({
    queryKey: ['queue-status'],
    queryFn: getQueueStatus,
    refetchInterval: 10000,
  })
}

export function useAddProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (url: string) => addProfile(url),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['profiles'] })
      queryClient.invalidateQueries({ queryKey: ['queue-status'] })
      if (data.status === 'finished') {
        toast.success('Profile already scraped')
      } else if (data.status === 'queued' || data.status === 'processing') {
        toast.success('Added to scraping queue')
      }
    },
    onError: () => {
      toast.error('Failed to add profile')
    },
  })
}

export function useDeleteProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteProfile(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profiles'] })
      queryClient.invalidateQueries({ queryKey: ['queue-status'] })
      toast.success('Profile deleted')
    },
    onError: () => {
      toast.error('Failed to delete profile')
    },
  })
}
