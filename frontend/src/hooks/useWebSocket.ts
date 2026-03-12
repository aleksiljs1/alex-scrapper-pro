import { useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { QueueUpdateEvent } from '../types/profile'

const WS_URL = import.meta.env.VITE_WS_URL || `ws://${window.location.host}/ws/queue-status`

export function useQueueWebSocket() {
  const ws = useRef<WebSocket | null>(null)
  const queryClient = useQueryClient()
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout>>()

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(WS_URL)

      ws.current.onmessage = (event) => {
        try {
          const data: QueueUpdateEvent = JSON.parse(event.data)
          if (data.event === 'status_change') {
            queryClient.invalidateQueries({ queryKey: ['profiles'] })
            queryClient.invalidateQueries({ queryKey: ['queue-status'] })
            queryClient.invalidateQueries({ queryKey: ['profile', data.data.id] })
          }
        } catch {
          // ignore parse errors
        }
      }

      ws.current.onclose = () => {
        reconnectTimeout.current = setTimeout(connect, 3000)
      }

      ws.current.onerror = () => {
        ws.current?.close()
      }
    } catch {
      reconnectTimeout.current = setTimeout(connect, 3000)
    }
  }, [queryClient])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimeout.current)
      ws.current?.close()
    }
  }, [connect])
}
