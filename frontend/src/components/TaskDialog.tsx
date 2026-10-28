import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../api'
import { SUGGEST_TITLE_REQUIRED, suggestErrorMessage } from '../suggestMessages'
import {
  PRIORITIES,
  type Priority,
  type Suggestion,
  type TaskInput,
} from '../types'

interface Props {
  heading?: string
  initialTitle?: string
  initialDescription?: string
  initialPriority?: Priority
  initialDueDate?: string | null
  onSave: (input: TaskInput) => Promise<void>
  onSuggest: (title: string, description: string) => Promise<Suggestion>
  onCancel: () => void
}

export default function TaskDialog({
  heading = '새 task',
  initialTitle = '',
  initialDescription = '',
  initialPriority = 'NORMAL',
  initialDueDate = null,
  onSave,
  onSuggest,
  onCancel,
}: Props) {
  const [title, setTitle] = useState(initialTitle)
  const [description, setDescription] = useState(initialDescription)
  const [priority, setPriority] = useState<Priority>(initialPriority)
  const [dueDate, setDueDate] = useState(initialDueDate ?? '')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  // AI 제안 상태. 저장 흐름(error, saving)과 섞지 않는다.
  const [suggesting, setSuggesting] = useState(false)
  const [suggestError, setSuggestError] = useState<string | null>(null)
  const [reason, setReason] = useState<string | null>(null)
  // 창이 닫힌 뒤에 늦게 온 제안 응답은 무시한다.
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  // 제안은 칸을 채우기만 한다. 저장은 사용자가 저장 버튼을 눌러야 한다.
  // 어떤 경우에도 저장 버튼은 막지 않는다.
  async function handleSuggest() {
    if (suggesting) return
    setSuggestError(null)
    setReason(null)
    // 사전 검사만 한다. 최종 판단은 API(D-004).
    if (!title.trim()) {
      setSuggestError(SUGGEST_TITLE_REQUIRED)
      return
    }
    setSuggesting(true)
    try {
      const suggestion = await onSuggest(title, description)
      if (!mounted.current) return
      setPriority(suggestion.priority)
      // 제안에 마감일이 없으면 사용자가 이미 넣은 날짜를 지우지 않는다.
      if (suggestion.due_date !== null) setDueDate(suggestion.due_date)
      setReason(suggestion.reason)
    } catch (err) {
      if (!mounted.current) return
      setSuggestError(
        suggestErrorMessage(err instanceof ApiError ? err.code : 'UNKNOWN'),
      )
    } finally {
      if (mounted.current) setSuggesting(false)
    }
  }

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
        <div className="suggest-row">
          <button type="button" onClick={handleSuggest} disabled={suggesting}>
            AI 제안
          </button>
          {suggesting && (
            <span className="suggest-status" role="status">
              제안 받는 중...
            </span>
          )}
        </div>
        {suggestError && (
          <p className="error suggest-error" role="alert">
            {suggestError}
          </p>
        )}
        <label>
          우선순위
          <select
            value={priority}
            onChange={(e) => {
              setPriority(e.target.value as Priority)
              setReason(null)
            }}
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
            onChange={(e) => {
              setDueDate(e.target.value)
              setReason(null)
            }}
          />
          <span className="hint">비우면 마감일이 없습니다.</span>
        </label>
        {reason && <p className="reason">AI 제안 근거: {reason}</p>}
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
