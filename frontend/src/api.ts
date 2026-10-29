import type {
  Briefing,
  Status,
  SubtaskInput,
  Suggestion,
  Task,
  TaskCandidate,
  TaskCreateInput,
  TaskInput,
  User,
  WeekPlan,
} from './types'

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

export const createTask = (input: TaskCreateInput) =>
  request<Task>('/tasks', {
    method: 'POST',
    body: JSON.stringify(input),
  })

// 기존 카드에 세부 항목을 붙인다. 한 번에 모두 붙거나 하나도 안 붙고, 세부 항목이 붙은 카드를 돌려준다.
export const addSubtasks = (taskId: number, items: SubtaskInput[]) =>
  request<Task>(`/tasks/${taskId}/subtasks`, {
    method: 'POST',
    body: JSON.stringify({ items }),
  })

export const updateTask = (id: number, input: TaskInput) =>
  request<Task>(`/tasks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })

// 입력 중인 제목과 설명으로 우선순위와 마감일을 제안받는다. 카드는 저장되지 않는다.
export const suggestTask = (title: string, description: string) =>
  request<Suggestion>('/tasks/suggest', {
    method: 'POST',
    body: JSON.stringify({ title, description }),
  })

// 주제(제목)에 맞는 할 일 후보를 제안받는다. 카드는 저장되지 않는다.
// 후보를 등록하는 것은 기존 createTask다.
export const suggestTasks = (title: string, description: string) =>
  request<{ items: TaskCandidate[] }>('/tasks/suggest-tasks', {
    method: 'POST',
    body: JSON.stringify({ title, description }),
  }).then((res) => res.items)

// 오늘 브리핑을 받는다. 본문은 없고 서버가 로그인한 사람의 완료 아닌 할 일을 모은다. 저장하지 않는다.
export const briefing = () =>
  request<Briefing>('/tasks/briefing', { method: 'POST' })

// 이번 주 계획을 받는다. 보내는 쪽은 오늘 브리핑과 같다. 저장하지 않는다.
export const weekplan = () =>
  request<WeekPlan>('/tasks/weekplan', { method: 'POST' })

export const deleteTask = (id: number) =>
  request<void>(`/tasks/${id}`, { method: 'DELETE' })

export const changeStatus = (id: number, status: Status) =>
  request<Task>(`/tasks/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
