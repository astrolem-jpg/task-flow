import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../api'
import {
  SUBTASKS_TOO_MANY,
  SUGGEST_TITLE_REQUIRED,
  subtasksAddErrorMessage,
  subtasksAddedMessage,
  subtasksPendingMessage,
  suggestErrorMessage,
} from '../suggestMessages'
import {
  PRIORITIES,
  SUBTASKS_MAX,
  type Priority,
  type Subtask,
  type SubtaskInput,
  type Suggestion,
  type TaskCandidate,
  type TaskCreateInput,
} from '../types'

// 미리 보기 목록에서 후보를 구분하는 번호가 붙은 후보.
type Candidate = TaskCandidate & { key: number }
// [저장] 때 카드와 함께 저장될 세부 항목(새 task 창).
type PendingSubtask = SubtaskInput & { key: number }

const priorityLabel = (p: Priority) =>
  PRIORITIES.find((x) => x.value === p)?.label ?? p

interface Props {
  heading?: string
  initialTitle?: string
  initialDescription?: string
  initialPriority?: Priority
  initialDueDate?: string | null
  initialSubtasks?: Subtask[]
  onSave: (input: TaskCreateInput) => Promise<void>
  onSuggest: (title: string, description: string) => Promise<Suggestion>
  onGenerate: (title: string, description: string) => Promise<TaskCandidate[]>
  // 수정 창에서만 넘긴다. 있으면 [모두 등록]이 그 카드에 세부 항목을 바로 붙인다.
  // 없으면(새 task 창) 후보를 이 창의 세부 목록에 담아 두었다가 [저장] 때 함께 저장한다.
  onAddSubtasks?: (items: SubtaskInput[]) => Promise<Subtask[]>
  onCancel: () => void
}

export default function TaskDialog({
  heading = '새 task',
  initialTitle = '',
  initialDescription = '',
  initialPriority = 'NORMAL',
  initialDueDate = null,
  initialSubtasks = [],
  onSave,
  onSuggest,
  onGenerate,
  onAddSubtasks,
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
  // AI로 할일 만들기 상태. 후보는 미리 보기일 뿐이고 [모두 등록]을 눌러야 세부 목록이 된다.
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState<string | null>(null)
  const [candidates, setCandidates] = useState<Candidate[]>([])
  // 수정 창: 이미 저장된 세부 목록. 새 task 창: [저장] 전까지 담아 둔 세부 목록(pending).
  const [savedSubtasks, setSavedSubtasks] = useState<Subtask[]>(initialSubtasks)
  const [pending, setPending] = useState<PendingSubtask[]>([])
  const [registering, setRegistering] = useState(false)
  const [registerInfo, setRegisterInfo] = useState<string | null>(null)
  const [registerError, setRegisterError] = useState<string | null>(null)
  const nextKey = useRef(0)
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

  // 제목(주제)으로 할 일 후보를 받아 미리 보기에 보인다. 아무것도 저장하지 않는다.
  async function handleGenerate() {
    if (generating || registering) return
    setGenerateError(null)
    setRegisterInfo(null)
    setRegisterError(null)
    setCandidates([])
    // 사전 검사만 한다. 최종 판단은 API(D-004).
    if (!title.trim()) {
      setGenerateError(SUGGEST_TITLE_REQUIRED)
      return
    }
    setGenerating(true)
    try {
      const items = await onGenerate(title, description)
      if (!mounted.current) return
      setCandidates(items.map((item) => ({ ...item, key: nextKey.current++ })))
    } catch (err) {
      if (!mounted.current) return
      setGenerateError(
        suggestErrorMessage(err instanceof ApiError ? err.code : 'UNKNOWN'),
      )
    } finally {
      if (mounted.current) setGenerating(false)
    }
  }

  // 남은 후보를 이 task의 세부 목록으로 등록한다. 후보는 개별 카드가 되지 않는다. (D-028)
  // 후보의 우선순위와 마감일은 쓰지 않는다. 카드의 값이 우선이다.
  async function handleRegisterAll() {
    if (registering || generating || candidates.length === 0) return
    setRegisterInfo(null)
    setRegisterError(null)
    const items: SubtaskInput[] = candidates.map((c) => ({
      title: c.title,
      description: c.description,
    }))

    if (!onAddSubtasks) {
      // 새 task 창: 카드가 아직 없다. 세부 목록에 담아 두고 [저장] 때 카드와 함께 저장한다.
      // 사전 검사만 한다. 최종 판단은 API(D-004).
      if (pending.length + items.length > SUBTASKS_MAX) {
        setRegisterError(SUBTASKS_TOO_MANY)
        return
      }
      setPending((prev) => [
        ...prev,
        ...items.map((item) => ({ ...item, key: nextKey.current++ })),
      ])
      setCandidates([])
      setRegisterInfo(subtasksPendingMessage(items.length))
      return
    }

    // 수정 창: 그 카드에 바로 붙인다. 한 번에 모두 붙거나 하나도 안 붙는다.
    setRegistering(true)
    try {
      const all = await onAddSubtasks(items)
      if (!mounted.current) return
      setSavedSubtasks(all)
      setCandidates([])
      setRegisterInfo(subtasksAddedMessage(items.length))
    } catch (err) {
      if (!mounted.current) return
      // 실패하면 후보를 그대로 남겨 다시 시도할 수 있게 한다.
      setRegisterError(
        subtasksAddErrorMessage(err instanceof ApiError ? err.code : 'UNKNOWN'),
      )
    } finally {
      if (mounted.current) setRegistering(false)
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
      // 담아 둔 세부 목록이 있으면 카드와 함께 보낸다(같은 저장). 없으면 이전과 똑같이 보낸다.
      await onSave({
        title,
        description,
        priority,
        due_date: dueDate === '' ? null : dueDate,
        ...(pending.length > 0 && {
          subtasks: pending.map((p) => ({
            title: p.title,
            description: p.description,
          })),
        }),
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
          <button
            type="button"
            onClick={handleGenerate}
            disabled={generating || registering}
          >
            AI로 할일 만들기
          </button>
          {generating && (
            <span className="suggest-status" role="status">
              할 일 만드는 중...
            </span>
          )}
        </div>
        {suggestError && (
          <p className="error suggest-error" role="alert">
            {suggestError}
          </p>
        )}
        {generateError && (
          <p className="error suggest-error" role="alert">
            {generateError}
          </p>
        )}
        {candidates.length > 0 && (
          <section className="candidates" aria-label="AI 할 일 후보">
            <p className="hint">
              AI 할 일 후보입니다. [모두 등록]을 누르면 이 task의 세부 목록이 됩니다. 원하지 않는 후보는 빼 주세요.
            </p>
            <ul>
              {candidates.map((c) => (
                <li key={c.key} className="candidate">
                  <div>
                    <strong>{c.title}</strong>
                    <span className="badge">우선순위 {priorityLabel(c.priority)}</span>
                    {c.due_date && <span className="badge">마감 {c.due_date}</span>}
                    {c.description && <p className="reason">{c.description}</p>}
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      setCandidates((prev) => prev.filter((x) => x.key !== c.key))
                    }
                    disabled={registering}
                  >
                    빼기
                  </button>
                </li>
              ))}
            </ul>
            <div className="actions">
              <button
                type="button"
                onClick={() => setCandidates([])}
                disabled={registering}
              >
                후보 닫기
              </button>
              <button type="button" onClick={handleRegisterAll} disabled={registering}>
                모두 등록
              </button>
              {registering && (
                <span className="suggest-status" role="status">
                  등록하는 중...
                </span>
              )}
            </div>
          </section>
        )}
        {registerInfo && (
          <p className="info" role="status">
            {registerInfo}
          </p>
        )}
        {registerError && (
          <p className="error suggest-error" role="alert">
            {registerError}
          </p>
        )}
        {savedSubtasks.length > 0 && (
          <section className="subtask-list" aria-label="세부 목록">
            <strong>세부 목록 ({savedSubtasks.length})</strong>
            <ul>
              {savedSubtasks.map((s) => (
                <li key={s.id}>
                  {s.title}
                  {s.description && <span className="reason"> - {s.description}</span>}
                </li>
              ))}
            </ul>
          </section>
        )}
        {pending.length > 0 && (
          <section className="subtask-list" aria-label="저장할 세부 목록">
            <strong>세부 목록 ({pending.length})</strong>
            <span className="hint">[저장]을 누르면 카드와 함께 저장됩니다.</span>
            <ul>
              {pending.map((p) => (
                <li key={p.key}>
                  {p.title}
                  {p.description && <span className="reason"> - {p.description}</span>}
                  <button
                    type="button"
                    onClick={() =>
                      setPending((prev) => prev.filter((x) => x.key !== p.key))
                    }
                    disabled={saving}
                  >
                    빼기
                  </button>
                </li>
              ))}
            </ul>
          </section>
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
