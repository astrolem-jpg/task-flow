export type Path = '/' | '/login'

// 주소만 바꾼다. 뒤로 가기 기록을 남기지 않아, 로그인한 뒤 뒤로 가도 로그인 화면으로
// 돌아가지 않는다(D-025). 어떤 화면을 보일지는 로그인 상태가 정하고 주소는 그 결과를 따른다.
export function navigate(path: Path) {
  if (window.location.pathname === path) return
  window.history.replaceState(null, '', path)
}
