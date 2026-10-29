import { useEffect, useRef, useState } from 'react'
import { ApiError, weekplan as fetchWeekPlan } from './api'
import { WEEKPLAN_EMPTY, weekplanErrorMessage } from './weekplanMessages'
import type { WeekPlan } from './types'

export type WeekPlanStatus = 'idle' | 'loading' | 'done' | 'empty' | 'error'

// 이번 주 계획 상태. 서버는 읽기만 하고 아무것도 저장하지 않는다. 표는 닫으면 사라진다.
export function useWeekPlan() {
  const [status, setStatus] = useState<WeekPlanStatus>('idle')
  const [plan, setPlan] = useState<WeekPlan | null>(null)
  const [message, setMessage] = useState<string | null>(null)
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

  async function run() {
    if (running.current) return
    running.current = true
    setStatus('loading')
    setMessage(null)
    try {
      const result = await fetchWeekPlan()
      if (!mounted.current) return
      if (result.days.length === 0) {
        // 할 일이 없으면 표 대신 안내만 보인다.
        setPlan(null)
        setMessage(WEEKPLAN_EMPTY)
        setStatus('empty')
        return
      }
      setPlan(result)
      setStatus('done')
    } catch (err) {
      if (!mounted.current) return
      setPlan(null)
      setMessage(weekplanErrorMessage(err instanceof ApiError ? err.code : 'UNKNOWN'))
      setStatus('error')
    } finally {
      running.current = false
    }
  }

  function close() {
    setPlan(null)
    setMessage(null)
    setStatus('idle')
  }

  return { status, plan, message, run, close }
}
