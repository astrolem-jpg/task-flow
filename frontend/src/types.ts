export type Status = 'TODO' | 'IN_PROGRESS' | 'DONE'

export const STATUSES: { value: Status; label: string }[] = [
  { value: 'TODO', label: '할 일' },
  { value: 'IN_PROGRESS', label: '진행 중' },
  { value: 'DONE', label: '완료' },
]

export interface User {
  id: number
  email: string
}

export interface Task {
  id: number
  title: string
  description: string
  status: Status
}
