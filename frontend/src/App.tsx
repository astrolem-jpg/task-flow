import { useEffect, useState } from 'react'
import {
  ApiError,
  addSubtasks,
  changeStatus,
  createTask,
  deleteTask,
  listTasks,
  suggestTask,
  suggestTasks,
  updateTask,
} from './api'
import BriefingCard from './BriefingCard'
import { useBriefing } from './useBriefing'
import Board from './components/Board'
import TaskDialog from './components/TaskDialog'
import type {
  Status,
  SubtaskInput,
  Task,
  TaskCreateInput,
  TaskInput,
  User,
} from './types'
import './App.css'

interface Props {
  user: User
  onLogout: () => Promise<void>
}

function App({ user, onLogout }: Props) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loggingOut, setLoggingOut] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Task | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const briefing = useBriefing()

  function loadTasks() {
    return listTasks()
      .then((list) => {
        setTasks(list)
        setLoadError(null)
      })
      .catch((err) =>
        // 이미 보이던 카드는 그대로 둔다(Q-08 미정, 임시 선택).
        setLoadError(err instanceof Error ? err.message : '불러오지 못했습니다.'),
      )
      .finally(() => setLoading(false))
  }

  function retry() {
    setLoading(true)
    void loadTasks()
  }

  useEffect(() => {
    void loadTasks()
  }, [])

  async function handleChangeStatus(id: number, status: Status) {
    try {
      const updated = await changeStatus(id, status)
      // 성공 응답을 받은 뒤에만 반영한다(D-011).
      setTasks((prev) => prev.map((t) => (t.id === id ? updated : t)))
      setActionError(null)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '상태를 바꾸지 못했습니다.')
      if (err instanceof ApiError && err.code === 'NOT_FOUND') {
        // 이미 없는 카드: 목록을 다시 읽어 실제와 맞춘다.
        listTasks().then(setTasks).catch(() => {})
      }
    }
  }

  async function handleCreate(input: TaskCreateInput) {
    const created = await createTask(input)
    // 성공 응답을 받은 뒤에만 화면에 반영한다(D-011).
    setTasks((prev) => [...prev, created])
    setDialogOpen(false)
  }

  // AI 후보를 수정 중인 카드의 세부 목록에 붙인다. 성공 응답을 받은 뒤에만 반영한다(D-011).
  // 창은 닫지 않고, 카드의 제목, 설명, 우선순위, 마감일은 바뀌지 않는다. (D-028)
  async function handleAddSubtasks(taskId: number, items: SubtaskInput[]) {
    const updated = await addSubtasks(taskId, items)
    setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
    return updated.subtasks
  }

  async function handleUpdate(input: TaskInput) {
    if (!editing) return
    try {
      const updated = await updateTask(editing.id, input)
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
      setActionError(null)
      setEditing(null)
    } catch (err) {
      if (err instanceof ApiError && err.code === 'NOT_FOUND') {
        // 이미 없는 카드: 목록을 다시 읽어 실제와 맞춘다.
        setActionError(err.message)
        setEditing(null)
        listTasks().then(setTasks).catch(() => {})
        return
      }
      throw err // 입력 내용을 남긴 채 창에서 안내한다.
    }
  }

  async function handleDelete(task: Task) {
    // 삭제 전에 한 번 묻는다(D-017).
    if (!window.confirm(`"${task.title}" 카드를 삭제할까요?`)) return
    try {
      await deleteTask(task.id)
      // 성공 응답을 받은 뒤에만 화면에서 없앤다(D-011).
      setTasks((prev) => prev.filter((t) => t.id !== task.id))
      setActionError(null)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '삭제하지 못했습니다.')
      if (err instanceof ApiError && err.code === 'NOT_FOUND') {
        // 이미 없는 카드: 목록을 다시 읽어 실제와 맞춘다.
        listTasks().then(setTasks).catch(() => {})
      }
    }
  }

  async function handleLogout() {
    if (loggingOut) return
    setLoggingOut(true)
    try {
      // 성공하면 로그인 화면으로 바뀌어 이 화면은 사라진다(D-025).
      await onLogout()
    } catch (err) {
      // 실패하면 로그인 상태를 유지하고 알린다.
      setActionError(err instanceof Error ? err.message : '로그아웃하지 못했습니다.')
      setLoggingOut(false)
    }
  }

  return (
    <main>
      <header>
        <h1>task-flow</h1>
        <div className="header-actions">
          <span className="user-email">{user.email}</span>
          <button onClick={() => setDialogOpen(true)}>새 task</button>
          <button type="button" onClick={handleLogout} disabled={loggingOut}>
            로그아웃
          </button>
        </div>
      </header>
      {loading && <p>불러오는 중...</p>}
      {loadError && (
        <p className="error" role="alert">
          {loadError} 저장된 카드는 그대로 남아 있습니다.{' '}
          <button type="button" onClick={retry} disabled={loading}>
            다시 시도
          </button>
        </p>
      )}
      {!loading && !loadError && tasks.length === 0 && (
        <p className="empty">카드가 없습니다. "새 task"를 눌러 추가해 보세요.</p>
      )}
      {actionError && <p className="error" role="alert">{actionError}</p>}
      <div className="briefing-bar">
        <button type="button" onClick={briefing.run} disabled={briefing.status === 'loading'}>
          {briefing.status === 'loading' ? '만드는 중…' : '오늘 브리핑'}
        </button>
        {briefing.status === 'error' && (
          <p className="error suggest-error" role="alert">{briefing.message}</p>
        )}
        {briefing.status === 'empty' && (
          <p className="empty" role="status">{briefing.message}</p>
        )}
        {briefing.status === 'done' && briefing.briefing && (
          <BriefingCard briefing={briefing.briefing} tasks={tasks} onClose={briefing.close} />
        )}
      </div>
      <Board
        tasks={tasks}
        onChangeStatus={handleChangeStatus}
        onEdit={setEditing}
        onDelete={handleDelete}
      />
      {dialogOpen && (
        <TaskDialog
          onSave={handleCreate}
          onSuggest={suggestTask}
          onGenerate={suggestTasks}
          onCancel={() => setDialogOpen(false)}
        />
      )}
      {editing && (
        <TaskDialog
          key={editing.id}
          heading="task 수정"
          initialTitle={editing.title}
          initialDescription={editing.description}
          initialPriority={editing.priority}
          initialDueDate={editing.due_date}
          initialSubtasks={editing.subtasks}
          onSave={handleUpdate}
          onSuggest={suggestTask}
          onGenerate={suggestTasks}
          onAddSubtasks={(items) => handleAddSubtasks(editing.id, items)}
          onCancel={() => setEditing(null)}
        />
      )}
    </main>
  )
}

export default App
