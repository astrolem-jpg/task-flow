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
  subtasks: Subtask[]
}

// 카드에 딸린 세부 항목. AI로 할일 만들기의 후보를 등록하면 여기에 쌓인다. (R-015, D-028)
export interface Subtask {
  id: number
  title: string
  description: string
}

export interface SubtaskInput {
  title: string
  description: string
}

// 카드 하나에 둘 수 있는 세부 항목의 최대 개수. 최종 판단은 API가 한다(D-004).
export const SUBTASKS_MAX = 20

// AI 제안(POST /tasks/suggest)의 응답. 제안만 하며 저장하지 않는다.
export interface Suggestion {
  priority: Priority
  due_date: string | null
  reason: string
}

// 오늘 브리핑(POST /tasks/briefing)의 응답. 제목은 없고 id만 온다. 저장하지 않는다.
export interface BriefingPick {
  id: number
  reason: string
}

export interface Briefing {
  top3: BriefingPick[]
  later: number[]
  cheer: string
}

// 새 task와 수정 입력이 보내는 값. due_date가 null이면 마감일 없음(수정에서는 지운다).
export interface TaskInput {
  title: string
  description: string
  priority: Priority
  due_date: string | null
}

// AI로 할일 만들기(POST /tasks/suggest-tasks)의 후보 한 건. 등록하기 전에는 저장되지 않는다.
export type TaskCandidate = TaskInput

// 새 task를 만들 때만 세부 항목을 함께 보낼 수 있다. 수정은 세부 항목을 바꾸지 않는다.
export type TaskCreateInput = TaskInput & { subtasks?: SubtaskInput[] }
