import { create } from 'zustand'
import type { ProfileStatus } from '../types/profile'

interface QueueItem {
  id: string
  url: string
  status: ProfileStatus
  name: string | null
  updated_at: string
}

interface QueueStore {
  items: QueueItem[]
  addOrUpdate: (item: QueueItem) => void
  clear: () => void
}

export const useQueueStore = create<QueueStore>((set) => ({
  items: [],
  addOrUpdate: (item) =>
    set((state) => {
      const existing = state.items.findIndex((i) => i.id === item.id)
      if (existing >= 0) {
        const updated = [...state.items]
        updated[existing] = item
        return { items: updated }
      }
      return { items: [item, ...state.items].slice(0, 50) }
    }),
  clear: () => set({ items: [] }),
}))
