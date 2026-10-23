import type { Status, Task, User } from './types'

// 화면 주소와 같은 호스트의 API를 부른다(D-025). localhost와 127.0.0.1은 서로 다른
// 사이트라서 호스트가 다르면 SameSite=Lax 로그인 쿠키가 전달되지 않는다.
const API_URL =
  import.meta.env.VITE_API_URL ?? `http://${window.location.hostname}:8000`

export class ApiError extends Error {
  code: string

  constructor(code: string, message: string) {
    super(message)
    this.code = code
  }
}

let onUnauthorized: (() => void) | null = null

// 로그인이 필요하다는 응답(401 UNAUTHORIZED)을 받으면 호출된다(D-025).
export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler
}

async function request<T>(
  path: string,
  init?: RequestInit,
  { notifyUnauthorized = true }: { notifyUnauthorized?: boolean } = {},
): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    })
  } catch {
    throw new ApiError('NETWORK', 'API에 연결할 수 없습니다.')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = body?.detail
    const code = detail?.code ?? 'UNKNOWN'
    if (notifyUnauthorized && res.status === 401 && code === 'UNAUTHORIZED') {
      onUnauthorized?.()
    }
    throw new ApiError(code, detail?.message ?? '요청을 처리하지 못했습니다.')
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

const credentialsBody = (email: string, password: string) =>
  JSON.stringify({ email, password })

export const signup = (email: string, password: string) =>
  request<User>('/auth/signup', {
    method: 'POST',
    body: credentialsBody(email, password),
  })

export const login = (email: string, password: string) =>
  request<User>('/auth/login', {
    method: 'POST',
    body: credentialsBody(email, password),
  })

export const logout = () => request<void>('/auth/logout', { method: 'POST' })

// 시작할 때 로그인 여부를 묻는 호출이다. 401은 호출한 쪽이 직접 처리한다.
export const me = () =>
  request<User>('/auth/me', undefined, { notifyUnauthorized: false })

export const listTasks = () => request<Task[]>('/tasks')

export const createTask = (title: string, description: string) =>
  request<Task>('/tasks', {
    method: 'POST',
    body: JSON.stringify({ title, description }),
  })

export const updateTask = (id: number, title: string, description: string) =>
  request<Task>(`/tasks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ title, description }),
  })

export const deleteTask = (id: number) =>
  request<void>(`/tasks/${id}`, { method: 'DELETE' })

export const changeStatus = (id: number, status: Status) =>
  request<Task>(`/tasks/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
