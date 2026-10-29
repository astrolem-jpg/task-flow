import type { Task, WeekPlan } from './types'
import './WeekPlanCard.css'

interface Props {
  plan: WeekPlan
  tasks: Task[]
  onClose: () => void
}

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

// 「2026-10-29 (목)」. 문자열을 로컬 날짜로 읽어 시간대에 따라 요일이 어긋나지 않게 한다.
function dayLabel(date: string): string {
  const [y, m, d] = date.split('-').map(Number)
  return `${date} (${WEEKDAYS[new Date(y, m - 1, d).getDay()]})`
}

// 이번 주 계획 표. 서버는 id만 주므로 제목은 지금의 카드 목록에서 id로 찾는다.
// 그 사이 지워졌거나 찾을 수 없는 id는 건너뛴다.
export default function WeekPlanCard({ plan, tasks, onClose }: Props) {
  const rows = plan.days.flatMap((day) => {
    const items = day.ids.flatMap((id) => {
      const title = tasks.find((t) => t.id === id)?.title
      return title === undefined ? [] : [{ id, title }]
    })
    return items.length === 0 ? [] : [{ date: day.date, items }]
  })

  return (
    <section className="weekplan-card" aria-label="이번 주 계획">
      <div className="weekplan-table" role="table">
        {rows.length === 0 && <p className="empty">계획된 카드를 찾을 수 없어요</p>}
        {rows.map((row) => (
          <div className="weekplan-row" role="row" key={row.date}>
            <strong className="weekplan-date" role="rowheader">
              {dayLabel(row.date)}
            </strong>
            <ul role="cell">
              {row.items.map((item) => (
                <li key={item.id}>{item.title}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <p className="weekplan-note">{plan.note}</p>
      <div className="actions">
        <button type="button" onClick={onClose}>
          닫기
        </button>
      </div>
    </section>
  )
}
