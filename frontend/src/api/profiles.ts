import client from './client'
import type { ProfileListResponse, QueueStatusResponse } from '../types/profile'

export async function addProfile(url: string) {
  const { data } = await client.post('/profiles', { url })
  return data
}

export async function getProfiles(params: {
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
}): Promise<ProfileListResponse> {
  // Strip empty strings so they aren't sent as query params
  const cleaned = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== '')
  )
  const { data } = await client.get('/profiles', { params: cleaned })
  return data
}

export async function getProfileById(id: string) {
  const { data } = await client.get(`/profiles/${id}`)
  return data
}

export async function getProfileByUrl(url: string) {
  const { data } = await client.get('/profiles/by-url', { params: { url } })
  return data
}

export async function deleteProfile(id: string) {
  const { data } = await client.delete(`/profiles/${id}`)
  return data
}

export async function getQueueStatus(): Promise<QueueStatusResponse> {
  const { data } = await client.get('/queue/status')
  return data
}
