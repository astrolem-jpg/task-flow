import type { Priority, Status } from './types.ts'

// 정렬과 기한 초과 판정은 화면이 한다. 규칙은 BUSINESS-RULES.md 3, 4절이다.
// "오늘"은 인자로 받는다(브라우저의 로컬 날짜). 시험할 때 날짜를 고정하려는 목적이다.
interface Ordered {
  id: number
  status: Status
  priority: Priority
  due_date: string | null
}

// 정렬에서 우선순위는 HIGH가 먼저다.
const PRIORITY_RANK: Record<Priority, number> = { HIGH: 0, NORMAL: 1, LOW: 2 }

// 로컬 날짜를 YYYY-MM-DD로 돌려준다.
export function todayString(now: Date = new Date()): string {
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${m}-${d}`
}

// 기한 초과 = 마감일이 오늘보다 이전이고, 상태가 완료가 아닐 때. 마감 당일은 아니다.
// YYYY-MM-DD는 문자열 비교가 날짜 비교와 같다.
export function isOverdue(
  task: Pick<Ordered, 'status' | 'due_date'>,
  today: string,
): boolean {
  return task.due_date !== null && task.due_date < today && task.status !== 'DONE'
}

// 기한 초과 -> 우선순위(HIGH 먼저) -> 빠른 마감일(없으면 맨 뒤) -> ID 순.
export function sortTasks<T extends Ordered>(tasks: T[], today: string): T[] {
  return [...tasks].sort((a, b) => {
    const overdue = Number(isOverdue(b, today)) - Number(isOverdue(a, today))
    if (overdue !== 0) return overdue
    const priority = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority]
    if (priority !== 0) return priority
    if (a.due_date !== b.due_date) {
      if (a.due_date === null) return 1
      if (b.due_date === null) return -1
      return a.due_date < b.due_date ? -1 : 1
    }
    return a.id - b.id
  })
}
