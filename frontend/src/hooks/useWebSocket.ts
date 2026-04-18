import { useEffect, useRef } from 'react'
import { connectRealtimeWS } from '../api/realtime.ws'
import { useAuth } from '../hooks/useAuth'

export const useWebSocket = (onMessage: (data: any) => void) => {
  const wsRef = useRef<any>(null)
  const { token } = useAuth()

  useEffect(() => {
    if (!token) return

    wsRef.current = connectRealtimeWS(token, onMessage)

    return () => {
      wsRef.current?.close()
    }
  }, [onMessage, token])

  return {
    send: (msg: string) => wsRef.current?.send(msg)
  }
}
