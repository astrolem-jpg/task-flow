import type { Briefing, Task } from './types'
import './BriefingCard.css'

interface Props {
  briefing: Briefing
  tasks: Task[]
  onClose: () => void
}

const NUMBERS = ['①', '②', '③']

// 오늘 브리핑 카드. 서버는 id만 주므로 제목은 지금의 카드 목록에서 id로 찾는다.
// 그 사이 지워졌거나 찾을 수 없는 id는 건너뛴다.
export default function BriefingCard({ briefing, tasks, onClose }: Props) {
  const titleOf = (id: number) => tasks.find((t) => t.id === id)?.title

  const first = briefing.top3.flatMap((pick) => {
    const title = titleOf(pick.id)
    return title === undefined ? [] : [{ id: pick.id, title, reason: pick.reason }]
  })
  const later = briefing.later.flatMap((id) => {
    const title = titleOf(id)
    return title === undefined ? [] : [{ id, title }]
  })

  return (
    <section className="briefing-card" aria-label="오늘 브리핑">
      {first.length > 0 && (
        <div>
          <strong>먼저 할 일</strong>
          <ol className="briefing-first">
            {first.map((item, i) => (
              <li key={item.id}>
                <span className="briefing-no">{NUMBERS[i]}</span>
                <span>
                  {item.title} — <span className="reason">{item.reason}</span>
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}
      {later.length > 0 && (
        <div>
          <strong>미뤄도 되는 일</strong>
          <ul className="briefing-later">
            {later.map((item) => (
              <li key={item.id}>{item.title}</li>
            ))}
          </ul>
        </div>
      )}
      <p className="briefing-cheer">{briefing.cheer}</p>
      <div className="actions">
        <button type="button" onClick={onClose}>
          닫기
        </button>
      </div>
    </section>
  )
}
