export type Status = 'TODO' | 'IN_PROGRESS' | 'DONE'

export const STATUSES: { value: Status; label: string }[] = [
  { value: 'TODO', label: '할 일' },
  { value: 'IN_PROGRESS', label: '진행 중' },
  { value: 'DONE', label: '완료' },
]

export type Priority = 'LOW' | 'NORMAL' | 'HIGH'

export const PRIORITIES: { value: Priority; label: string }[] = [
  { value: 'LOW', label: '낮음' },
  { value: 'NORMAL', label: '보통' },
  { value: 'HIGH', label: '높음' },
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
  priority: Priority
  due_date: string | null
}

// 새 task와 수정 입력이 보내는 값. due_date가 null이면 마감일 없음(수정에서는 지운다).
export interface TaskInput {
  title: string
  description: string
  priority: Priority
  due_date: string | null
}
