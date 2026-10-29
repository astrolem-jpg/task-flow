// 오늘 브리핑이 실패했거나 비었을 때 보일 문구. API의 오류 코드로 고른다(API-SPEC-CHANGE.md 10절).
export const BRIEFING_UNAVAILABLE = '지금은 브리핑을 쓸 수 없습니다'
export const BRIEFING_FAILED = '브리핑을 받지 못했습니다'
export const BRIEFING_EMPTY = '오늘은 비어 있어요'

// 503(AI_DISABLED, AI_BUSY)과 API에 연결할 수 없는 경우는 브리핑을 쓸 수 없는 상황이다.
// 502(SUGGEST_FAILED)와 그 밖의 오류는 받지 못한 것이다.
export function briefingErrorMessage(code: string): string {
  switch (code) {
    case 'AI_DISABLED':
    case 'AI_BUSY':
    case 'NETWORK':
      return BRIEFING_UNAVAILABLE
    default:
      return BRIEFING_FAILED
  }
}
