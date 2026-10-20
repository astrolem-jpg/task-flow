import { useEffect, useState } from 'react'
import {
  ApiError,
  changeStatus,
  createTask,
  deleteTask,
  listTasks,
  updateTask,
} from './api'
import Board from './components/Board'
import TaskDialog from './components/TaskDialog'
import type { Status, Task } from './types'
import './App.css'

function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Task | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

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

  async function handleCreate(title: string, description: string) {
    const created = await createTask(title, description)
    // 성공 응답을 받은 뒤에만 화면에 반영한다(D-011).
    setTasks((prev) => [...prev, created])
    setDialogOpen(false)
  }

  async function handleUpdate(title: string, description: string) {
    if (!editing) return
    try {
      const updated = await updateTask(editing.id, title, description)
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

  return (
    <main>
      <header>
        <h1>task-flow</h1>
        <button onClick={() => setDialogOpen(true)}>새 task</button>
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
      <Board
        tasks={tasks}
        onChangeStatus={handleChangeStatus}
        onEdit={setEditing}
        onDelete={handleDelete}
      />
      {dialogOpen && (
        <TaskDialog
          onSave={handleCreate}
          onCancel={() => setDialogOpen(false)}
        />
      )}
      {editing && (
        <TaskDialog
          key={editing.id}
          heading="task 수정"
          initialTitle={editing.title}
          initialDescription={editing.description}
          onSave={handleUpdate}
          onCancel={() => setEditing(null)}
        />
      )}
    </main>
  )
}

export default App
