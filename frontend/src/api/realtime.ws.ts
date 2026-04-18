export const connectRealtimeWS = (token: string, onMsg: (d: any) => void) => {
  let ws: WebSocket | null = null
  let reconnectAttempts = 0
  const maxReconnectAttempts = 10
  let reconnectTimeout: NodeJS.Timeout | null = null
  let heartbeatInterval: NodeJS.Timeout | null = null

  const connect = () => {
    try {
      ws = new WebSocket(`ws://localhost:8000/ws/transactions?token=${token}`)

      ws.onopen = () => {
        console.log('WebSocket connected')
        reconnectAttempts = 0
        
        // Start heartbeat
        heartbeatInterval = setInterval(() => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, 25000) // Send ping every 25 seconds
      }

      ws.onmessage = (e) => {
        const data = JSON.parse(e.data)
        // Ignore heartbeat messages on client
        if (data.type !== 'heartbeat') {
          onMsg(data)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      ws.onclose = () => {
        console.log('WebSocket closed, attempting to reconnect...')
        
        // Clear heartbeat
        if (heartbeatInterval) {
          clearInterval(heartbeatInterval)
          heartbeatInterval = null
        }

        // Reconnect with exponential backoff
        if (reconnectAttempts < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000)
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1}/${maxReconnectAttempts})`)
          reconnectAttempts++
          
          reconnectTimeout = setTimeout(() => {
            connect()
          }, delay)
        } else {
          console.error('Max reconnection attempts reached')
        }
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
    }
  }

  connect()

  // Return close function
  return {
    close: () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
      if (heartbeatInterval) clearInterval(heartbeatInterval)
      if (ws) ws.close()
    },
    send: (msg: string) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(msg)
      }
    }
  }
}
