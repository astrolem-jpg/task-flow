import { useEffect, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

function App() {
  const [apiStatus, setApiStatus] = useState('확인 중...')

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => res.json())
      .then((data) => setApiStatus(data.status))
      .catch(() => setApiStatus('API에 연결할 수 없음'))
  }, [])

  return (
    <main>
      <h1>task-flow</h1>
      <p>API 상태: {apiStatus}</p>
    </main>
  )
}

export default App
