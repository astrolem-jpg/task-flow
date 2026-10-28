// AI 제안이 실패했을 때 보일 문구. API의 오류 코드로 고른다(API-SPEC-CHANGE.md 7절).
export const SUGGEST_TITLE_REQUIRED = '제목을 입력해 주세요.'
export const SUGGEST_UNAVAILABLE = '지금은 AI 제안을 쓸 수 없습니다. 직접 입력해 주세요.'
export const SUGGEST_FAILED = '제안을 못 받았습니다. 다시 제안 버튼을 눌러 주세요.'

// 503(AI_DISABLED, AI_BUSY)과 API에 연결할 수 없는 경우는 AI를 쓸 수 없는 상황이다.
// 502(SUGGEST_FAILED)와 그 밖의 오류는 다시 눌러 볼 수 있다.
export function suggestErrorMessage(code: string): string {
  switch (code) {
    case 'AI_DISABLED':
    case 'AI_BUSY':
    case 'NETWORK':
      return SUGGEST_UNAVAILABLE
    default:
      return SUGGEST_FAILED
  }
}
