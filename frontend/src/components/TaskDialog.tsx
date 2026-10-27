import { useState } from 'react'
import { PRIORITIES, type Priority, type TaskInput } from '../types'

interface Props {
  heading?: string
  initialTitle?: string
  initialDescription?: string
  initialPriority?: Priority
  initialDueDate?: string | null
  onSave: (input: TaskInput) => Promise<void>
  onCancel: () => void
}

export default function TaskDialog({
  heading = '새 task',
  initialTitle = '',
  initialDescription = '',
  initialPriority = 'NORMAL',
  initialDueDate = null,
  onSave,
  onCancel,
}: Props) {
  const [title, setTitle] = useState(initialTitle)
  const [description, setDescription] = useState(initialDescription)
  const [priority, setPriority] = useState<Priority>(initialPriority)
  const [dueDate, setDueDate] = useState(initialDueDate ?? '')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (saving) return
    // 사전 검사만 한다. 최종 판단은 API(D-004).
    if (!title.trim()) {
      setError('제목을 입력해 주세요.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      // 마감일을 비우면 null이다(마감일 없음, 수정에서는 지운다).
      await onSave({
        title,
        description,
        priority,
        due_date: dueDate === '' ? null : dueDate,
      })
    } catch (err) {
      // 실패하면 입력한 내용을 남겨 둔다.
      setError(err instanceof Error ? err.message : '저장하지 못했습니다.')
      setSaving(false)
    }
  }

  return (
    <div className="overlay" role="dialog" aria-modal="true" aria-label={heading}>
      <form className="dialog" onSubmit={submit}>
        <h2>{heading}</h2>
        <label>
          제목 (필수)
          <input
            autoFocus
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <label>
          설명 (선택)
          <textarea
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <label>
          우선순위
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value as Priority)}
          >
            {PRIORITIES.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          마감일 (선택)
          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
          <span className="hint">비우면 마감일이 없습니다.</span>
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="actions">
          <button type="button" onClick={onCancel} disabled={saving}>
            취소
          </button>
          <button type="submit" disabled={saving}>
            저장
          </button>
        </div>
      </form>
    </div>
  )
}
