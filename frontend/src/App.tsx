import { useEffect, useState } from 'react'

type ConnectionStatus = 'checking' | 'connected' | 'failed'

function App() {
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>('checking')

  useEffect(() => {
    async function checkBackendHealth() {
      try {
        const response = await fetch('http://127.0.0.1:8000/health')

        if (!response.ok) {
          throw new Error(`Health check failed with status ${response.status}`)
        }

        await response.json()
        setConnectionStatus('connected')
      } catch {
        setConnectionStatus('failed')
      }
    }

    void checkBackendHealth()
  }, [])

  const connectionMessage = {
    checking: 'Checking...',
    connected: 'Connected',
    failed: 'Connection failed',
  }[connectionStatus]

  return (
    <main className="welcome">
      <p className="eyebrow">Project foundation</p>
      <h1>SentimentIQ</h1>
      <p className="intro">
        A starting point for sentiment and aspect analysis across product
        reviews and campus feedback.
      </p>
      <p className="status" role="status" aria-live="polite">
        Backend status: {connectionMessage}
      </p>
    </main>
  )
}

export default App
