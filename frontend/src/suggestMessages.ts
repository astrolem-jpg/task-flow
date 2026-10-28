// AI 제안이 실패했을 때 보일 문구. API의 오류 코드로 고른다(API-SPEC-CHANGE.md 7절).
export const SUGGEST_TITLE_REQUIRED = '제목을 입력해 주세요.'
export const SUGGEST_UNAVAILABLE = '지금은 AI 제안을 쓸 수 없습니다. 직접 입력해 주세요.'
export const SUGGEST_FAILED = '제안을 못 받았습니다. 다시 제안 버튼을 눌러 주세요.'

// AI로 할일 만들기: 후보를 task의 세부 목록으로 등록한 결과 안내. (D-028)
// 새 task 창에서는 [저장]을 눌러야 카드와 함께 저장되고, 수정 창에서는 바로 붙는다.
export const subtasksPendingMessage = (count: number) =>
  `후보 ${count}개를 세부 목록에 담았습니다. [저장]을 누르면 카드와 함께 저장됩니다.`
export const subtasksAddedMessage = (count: number) =>
  `세부 목록에 ${count}개를 추가했습니다.`
export const SUBTASKS_ADD_FAILED =
  '세부 목록에 추가하지 못했습니다. 후보는 그대로 있으니 [모두 등록]을 다시 눌러 주세요.'
export const SUBTASKS_TOO_MANY = '세부 항목은 카드 하나에 최대 20개입니다.'

// 세부 목록 추가 실패 문구. 20개 초과만 따로 알리고 나머지는 다시 시도하게 한다.
export function subtasksAddErrorMessage(code: string): string {
  return code === 'TOO_MANY_SUBTASKS' ? SUBTASKS_TOO_MANY : SUBTASKS_ADD_FAILED
}

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
