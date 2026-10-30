import { useEffect, useRef, useState } from 'react'
import { ApiError, changeStatus, command, createTask, updateTask } from './api'
import { PRIORITIES } from './types'
import type { CommandAction, Task } from './types'
import './CommandBar.css'

const TEXT_MAX = 200
const UNAVAILABLE = '지금은 지시할 수 없습니다'
const NOT_UNDERSTOOD = '알아듣지 못했습니다'
const NOTHING_TO_CHANGE = '바꿀 카드를 찾지 못했습니다'

// 서버의 오류 코드로 문구를 고른다. 422는 서버가 준 이유를 그대로 보인다.
// 503(AI_DISABLED, AI_BUSY)과 API에 연결할 수 없는 경우는 지시할 수 없는 상황이고,
// 502(SUGGEST_FAILED)와 그 밖의 오류는 알아듣지 못한 것이다.
function commandErrorMessage(err: unknown): string {
  const code = err instanceof ApiError ? err.code : 'UNKNOWN'
  switch (code) {
    case 'INVALID_COMMAND':
      return err instanceof Error ? err.message : NOT_UNDERSTOOD
    case 'AI_DISABLED':
    case 'AI_BUSY':
    case 'NETWORK':
      return UNAVAILABLE
    default:
      return NOT_UNDERSTOOD
  }
}

// 확인 카드 한 줄. due/done은 지금 카드(task)를 함께 들고 있다. 적용할 때 그 카드의 값을 그대로 쓴다.
interface Item {
  action: CommandAction
  task: Task | null
}

const priorityLabel = (value: string | null) =>
  PRIORITIES.find((p) => p.value === value)?.label ?? ''

function describe({ action, task }: Item): string {
  if (action.kind === 'add') {
    const extra = [priorityLabel(action.priority), action.due_date && `마감 ${action.due_date}`]
      .filter(Boolean)
      .join(' · ')
    return `새 카드: ${action.title}${extra ? ` (${extra})` : ''}`
  }
  if (action.kind === 'done') return `${task?.title} → 완료로`
  return `${task?.title}(${task?.due_date ? `지금 마감 ${task.due_date}` : '지금 마감 없음'}) → 마감을 ${action.due_date}(으)로`
}

// 한 건을 기존 API로 적용한다. 서버 PATCH는 제목이 필수이고 설명을 덮어쓰므로,
// 마감일만 바꿀 때도 지금 카드의 제목, 설명, 우선순위를 그대로 보낸다.
async function apply({ action, task }: Item) {
  if (action.kind === 'add') {
    await createTask({
      title: action.title ?? '',
      description: '',
      priority: action.priority ?? 'NORMAL',
      due_date: action.due_date,
    })
  } else if (action.kind === 'done' && task) {
    await changeStatus(task.id, 'DONE')
  } else if (action.kind === 'due' && task) {
    await updateTask(task.id, {
      title: task.title,
      description: task.description,
      priority: task.priority,
      due_date: action.due_date,
    })
  }
}

interface Props {
  tasks: Task[]
  onApplied: () => Promise<void>
}

// 한 문장으로 시키기. 서버는 제안만 하고, 사용자가 [적용]을 누르면 카드마다 기존 API를 한 번씩 부른다.
export default function CommandBar({ tasks, onApplied }: Props) {
  const [text, setText] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'applying'>('idle')
  const [items, setItems] = useState<Item[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const [isError, setIsError] = useState(false)
  // state는 다음 렌더에야 바뀌므로, 같은 틱의 두 번째 클릭은 ref로 막는다.
  const running = useRef(false)
  // 화면이 사라진 뒤에 늦게 온 응답은 무시한다.
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  function show(next: string | null, error = false) {
    setMessage(next)
    setIsError(error)
  }

  async function run() {
    const sentence = text.trim()
    if (running.current || !sentence) return
    running.current = true
    setStatus('loading')
    setItems([])
    show(null)
    try {
      const result = await command(sentence)
      if (!mounted.current) return
      if (result.ask) {
        show(result.ask)
        return
      }
      // 그 사이 사라진 카드의 action은 뺀다.
      const found = result.actions.flatMap((action): Item[] => {
        if (action.kind === 'add') return [{ action, task: null }]
        const task = tasks.find((t) => t.id === action.id)
        return task ? [{ action, task }] : []
      })
      if (found.length === 0) show(NOTHING_TO_CHANGE)
      setItems(found)
    } catch (err) {
      if (!mounted.current) return
      show(commandErrorMessage(err), true)
    } finally {
      running.current = false
      if (mounted.current) setStatus('idle')
    }
  }

  async function applyAll() {
    if (running.current) return
    running.current = true
    setStatus('applying')
    let failed = 0
    let firstError = ''
    // 한 건이 실패해도 나머지는 계속하고, 끝나면 목록을 다시 받아 실제와 맞춘다.
    for (const item of items) {
      try {
        await apply(item)
      } catch (err) {
        failed += 1
        if (!firstError) firstError = err instanceof Error ? err.message : ''
      }
    }
    try {
      await onApplied()
    } finally {
      running.current = false
      if (mounted.current) {
        setStatus('idle')
        if (failed === 0) {
          setItems([])
          setText('')
          show(null)
        } else {
          show(`${items.length}개 중 ${failed}개를 바꾸지 못했습니다. ${firstError}`, true)
          setItems([])
        }
      }
    }
  }

  function cancel() {
    setItems([])
    show(null)
  }

  const busy = status !== 'idle'

  return (
    <section className="command-bar" aria-label="한 문장으로 시키기">
      <form
        className="command-form"
        onSubmit={(e) => {
          e.preventDefault()
          void run()
        }}
      >
        <input
          type="text"
          value={text}
          maxLength={TEXT_MAX}
          placeholder="예: 내일까지 보고서 쓰기 추가해 줘"
          aria-label="시킬 말"
          disabled={busy}
          onChange={(e) => setText(e.target.value)}
        />
        <button type="submit" disabled={busy || !text.trim()}>
          {status === 'loading' ? '알아듣는 중...' : '시키기'}
        </button>
      </form>
      {message && (
        <p className={isError ? 'error suggest-error' : 'command-ask'} role={isError ? 'alert' : 'status'}>
          {message}
        </p>
      )}
      {items.length > 0 && (
        <div className="command-card">
          <strong>이렇게 바꿀까요? {items.length}개</strong>
          <ul>
            {items.map((item, i) => (
              <li key={i}>{describe(item)}</li>
            ))}
          </ul>
          <div className="actions">
            <button type="button" onClick={cancel} disabled={busy}>
              취소
            </button>
            <button type="button" onClick={() => void applyAll()} disabled={busy}>
              {status === 'applying' ? '바꾸는 중...' : '적용'}
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
