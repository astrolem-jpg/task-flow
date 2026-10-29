import { useEffect, useRef, useState } from 'react'
import { ApiError, briefing as fetchBriefing } from './api'
import { BRIEFING_EMPTY, briefingErrorMessage } from './briefingMessages'
import type { Briefing } from './types'

export type BriefingStatus = 'idle' | 'loading' | 'done' | 'empty' | 'error'

// 오늘 브리핑 상태. 서버는 읽기만 하고 아무것도 저장하지 않는다. 카드는 닫으면 사라진다.
export function useBriefing() {
  const [status, setStatus] = useState<BriefingStatus>('idle')
  const [briefing, setBriefing] = useState<Briefing | null>(null)
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
      const result = await fetchBriefing()
      if (!mounted.current) return
      if (result.top3.length === 0 && result.later.length === 0) {
        // 할 일이 없으면 카드 대신 안내만 보인다.
        setBriefing(null)
        setMessage(BRIEFING_EMPTY)
        setStatus('empty')
        return
      }
      setBriefing(result)
      setStatus('done')
    } catch (err) {
      if (!mounted.current) return
      setBriefing(null)
      setMessage(briefingErrorMessage(err instanceof ApiError ? err.code : 'UNKNOWN'))
      setStatus('error')
    } finally {
      running.current = false
    }
  }

  function close() {
    setBriefing(null)
    setMessage(null)
    setStatus('idle')
  }

  return { status, briefing, message, run, close }
}
