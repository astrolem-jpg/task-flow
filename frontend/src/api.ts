import type { Status, Task } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

export class ApiError extends Error {
  code: string

  constructor(code: string, message: string) {
    super(message)
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json' },
    })
  } catch {
    throw new ApiError('NETWORK', 'API에 연결할 수 없습니다.')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = body?.detail
    throw new ApiError(
      detail?.code ?? 'UNKNOWN',
      detail?.message ?? '요청을 처리하지 못했습니다.',
    )
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

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
  request<Task>(`/tasks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
