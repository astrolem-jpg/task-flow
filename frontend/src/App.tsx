import { useEffect, useState } from 'react'
import { createTask, listTasks } from './api'
import Board from './components/Board'
import TaskDialog from './components/TaskDialog'
import type { Task } from './types'
import './App.css'

function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    listTasks()
      .then((list) => {
        setTasks(list)
        setLoadError(null)
      })
      .catch((err) =>
        setLoadError(err instanceof Error ? err.message : '불러오지 못했습니다.'),
      )
  }, [])

  async function handleCreate(title: string, description: string) {
    const created = await createTask(title, description)
    // 성공 응답을 받은 뒤에만 화면에 반영한다(D-011).
    setTasks((prev) => [...prev, created])
    setDialogOpen(false)
  }

  return (
    <main>
      <header>
        <h1>task-flow</h1>
        <button onClick={() => setDialogOpen(true)}>새 task</button>
      </header>
      {loadError && <p className="error" role="alert">{loadError}</p>}
      <Board tasks={tasks} />
      {dialogOpen && (
        <TaskDialog
          onSave={handleCreate}
          onCancel={() => setDialogOpen(false)}
        />
      )}
    </main>
  )
}

export default App
