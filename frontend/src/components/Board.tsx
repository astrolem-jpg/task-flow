import { STATUSES, type Task } from '../types'

interface Props {
  tasks: Task[]
}

export default function Board({ tasks }: Props) {
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
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
