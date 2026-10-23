import { useEffect, useState } from 'react'
import App from './App'
import { ApiError, logout, me, setUnauthorizedHandler } from './api'
import LoginPage from './components/LoginPage'
import { navigate } from './route'
import type { User } from './types'

type AuthState =
  | { status: 'checking' }
  | { status: 'user'; user: User }
  | { status: 'anonymous'; notice: string | null }
  | { status: 'unreachable'; message: string }

const EXPIRED_NOTICE = '로그인이 만료되었습니다. 다시 로그인해 주세요.'

// 로그인 여부를 확인한 결과에 따라 보드 또는 로그인 화면을 보여 주고, 주소를 맞춘다(D-025).
function fetchAuthState(): Promise<AuthState> {
  return me().then(
    (user): AuthState => ({ status: 'user', user }),
    (err): AuthState => {
      if (err instanceof ApiError && err.code === 'UNAUTHORIZED') {
        return { status: 'anonymous', notice: null }
      }
      // API에 연결할 수 없는 경우는 로그인 화면으로 보내지 않는다.
      return {
        status: 'unreachable',
        message: err instanceof Error ? err.message : '로그인 상태를 확인하지 못했습니다.',
      }
    },
  )
}

function AuthGate() {
  const [state, setState] = useState<AuthState>({ status: 'checking' })

  useEffect(() => {
    let cancelled = false
    void fetchAuthState().then((next) => {
      if (!cancelled) setState(next)
    })
    return () => {
      cancelled = true
    }
  }, [])

  // 사용 중 로그인이 필요하다는 응답을 받으면 로그인 화면으로 보낸다.
  useEffect(() => {
    if (state.status !== 'user') return
    setUnauthorizedHandler(() =>
      setState((prev) =>
        prev.status === 'user' ? { status: 'anonymous', notice: EXPIRED_NOTICE } : prev,
      ),
    )
    return () => setUnauthorizedHandler(null)
  }, [state.status])

  useEffect(() => {
    if (state.status === 'anonymous') navigate('/login')
    else if (state.status === 'user') navigate('/')
  }, [state.status])

  function retry() {
    setState({ status: 'checking' })
    void fetchAuthState().then(setState)
  }

  // API가 성공한 뒤에만 로그인 화면으로 바꾼다. 실패하면 던져서 보드가 알리게 한다(D-011).
  async function signOut() {
    await logout()
    setState({ status: 'anonymous', notice: null })
  }

  switch (state.status) {
    case 'checking':
      return (
        <main>
          <p>확인 중...</p>
        </main>
      )
    case 'unreachable':
      return (
        <main>
          <p className="error" role="alert">
            {state.message}{' '}
            <button type="button" onClick={retry}>
              다시 시도
            </button>
          </p>
        </main>
      )
    case 'anonymous':
      return (
        <LoginPage
          notice={state.notice}
          onLoggedIn={(user) => setState({ status: 'user', user })}
        />
      )
    case 'user':
      // key: 사용자가 바뀌면 이전 사용자의 카드 상태를 이어받지 않는다.
      return <App key={state.user.id} user={state.user} onLogout={signOut} />
  }
}

export default AuthGate
