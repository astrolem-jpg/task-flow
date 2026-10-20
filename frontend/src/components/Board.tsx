import { STATUSES, type Status, type Task } from '../types'

interface Props {
  tasks: Task[]
  onChangeStatus: (id: number, status: Status) => void
  onEdit: (task: Task) => void
}

export default function Board({ tasks, onChangeStatus, onEdit }: Props) {
  return (
    <div className="board">
      {STATUSES.map((s) => {
        const items = tasks
          .filter((t) => t.status === s.value)
          .sort((a, b) => a.id - b.id)
        return (
          <section key={s.value} className="column">
            <h2>{s.label}</h2>
            <ul>
              {items.map((t) => (
                <li key={t.id} className="card">
                  <strong>{t.title}</strong>
                  <span className="badge">{s.label}</span>
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
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
