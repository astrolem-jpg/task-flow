import { isOverdue, sortTasks, todayString } from '../taskOrder'
import { PRIORITIES, STATUSES, type Status, type Task } from '../types'

const PRIORITY_LABEL = Object.fromEntries(
  PRIORITIES.map((p) => [p.value, p.label]),
)

interface Props {
  tasks: Task[]
  onChangeStatus: (id: number, status: Status) => void
  onEdit: (task: Task) => void
  onDelete: (task: Task) => void
}

export default function Board({
  tasks,
  onChangeStatus,
  onEdit,
  onDelete,
}: Props) {
  const today = todayString()
  return (
    <div className="board">
      {STATUSES.map((s) => {
        // 상태 열 안에서만 정렬한다. 기한 초과가 맨 위에 온다.
        const items = sortTasks(
          tasks.filter((t) => t.status === s.value),
          today,
        )
        return (
          <section key={s.value} className="column">
            <h2>{s.label}</h2>
            <ul>
              {items.map((t) => (
                <li
                  key={t.id}
                  className={isOverdue(t, today) ? 'card overdue' : 'card'}
                >
                  <strong>{t.title}</strong>
                  <span className="badge">{s.label}</span>
                  <span className="meta">
                    <span className="badge">
                      우선순위 {PRIORITY_LABEL[t.priority]}
                    </span>
                    {t.due_date && (
                      <span className="badge">마감 {t.due_date}</span>
                    )}
                    {isOverdue(t, today) && (
                      <span className="badge overdue-label">기한 초과</span>
                    )}
                  </span>
                  {t.subtasks.length > 0 && (
                    <details className="subtasks">
                      <summary>세부 목록 ({t.subtasks.length})</summary>
                      <ul>
                        {t.subtasks.map((s) => (
                          <li key={s.id}>
                            {s.title}
                            {s.description && (
                              <span className="reason"> - {s.description}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                  <label className="status-select">
                    상태 변경
                    <select
                      value={t.status}
                      onChange={(e) =>
                        onChangeStatus(t.id, e.target.value as Status)
                      }
                    >
                      {STATUSES.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button type="button" onClick={() => onEdit(t)}>
                    수정
                  </button>
                  <button type="button" onClick={() => onDelete(t)}>
                    삭제
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
