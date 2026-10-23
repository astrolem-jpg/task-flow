import { useState } from 'react'
import { login, signup } from '../api'
import type { User } from '../types'

interface Props {
  notice: string | null
  onLoggedIn: (user: User) => void
}

type Mode = 'login' | 'signup'

export default function LoginPage({ notice, onLoggedIn }: Props) {
  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)
  const [showNotice, setShowNotice] = useState(true)
  const [busy, setBusy] = useState(false)

  function switchMode(next: Mode) {
    setMode(next)
    setError(null)
    setInfo(null)
    setPassword('')
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    // 사전 검사만 한다. 최종 판단은 API(D-004).
    if (!email.trim()) {
      setError('이메일을 입력해 주세요.')
      return
    }
    if (!password) {
      setError('비밀번호를 입력해 주세요.')
      return
    }
    setBusy(true)
    setError(null)
    setInfo(null)
    setShowNotice(false)
    try {
      if (mode === 'login') {
        // 성공하면 화면이 보드로 바뀌므로 이 컴포넌트는 사라진다.
        onLoggedIn(await login(email, password))
        return
      }
      const created = await signup(email, password)
      // 가입해도 자동으로 로그인하지 않는다. 로그인 화면으로 돌아가 이메일은 남겨 둔다(D-025).
      setMode('login')
      setEmail(created.email)
      setInfo('가입되었습니다. 로그인해 주세요.')
    } catch (err) {
      setError(err instanceof Error ? err.message : '요청을 처리하지 못했습니다.')
    }
    // 실패하거나 가입한 뒤에는 입력한 이메일은 남기고 비밀번호는 지운다.
    setPassword('')
    setBusy(false)
  }

  const isSignup = mode === 'signup'

  return (
    <main>
      <h1>task-flow</h1>
      <form className="auth" onSubmit={submit} noValidate>
        <h2>{isSignup ? '가입' : '로그인'}</h2>
        {showNotice && notice && (
          <p className="error" role="alert">
            {notice}
          </p>
        )}
        {info && (
          <p className="info" role="status">
            {info}
          </p>
        )}
        <label>
          이메일
          <input
            type="email"
            name="email"
            autoFocus
            autoComplete={isSignup ? 'email' : 'username'}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          비밀번호
          <input
            type="password"
            name="password"
            autoComplete={isSignup ? 'new-password' : 'current-password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {isSignup && <p className="hint">비밀번호는 8자 이상 128자 이하로 입력해 주세요.</p>}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <div className="actions">
          <button
            type="button"
            onClick={() => switchMode(isSignup ? 'login' : 'signup')}
            disabled={busy}
          >
            {isSignup ? '로그인으로 돌아가기' : '가입하기'}
          </button>
          <button type="submit" disabled={busy}>
            {isSignup ? '가입' : '로그인'}
          </button>
        </div>
      </form>
    </main>
  )
}
