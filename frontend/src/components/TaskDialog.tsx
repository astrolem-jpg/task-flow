import { useState } from 'react'

interface Props {
  onSave: (title: string, description: string) => Promise<void>
  onCancel: () => void
}

export default function TaskDialog({ onSave, onCancel }: Props) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
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
      await onSave(title, description)
    } catch (err) {
      // 실패하면 입력한 내용을 남겨 둔다.
      setError(err instanceof Error ? err.message : '저장하지 못했습니다.')
      setSaving(false)
    }
  }

  return (
    <div className="overlay" role="dialog" aria-modal="true" aria-label="새 task">
      <form className="dialog" onSubmit={submit}>
        <h2>새 task</h2>
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
