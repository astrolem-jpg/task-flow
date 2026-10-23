fetch('/api/tasks')          //서버에 GET /api/tasks 요청을 보낸다. ==> 내 Task 목록을 가져온다.
    .then(r => r.json())          //서버에서 받은 응답을 JSON으로 변환한다. 받은 답을 읽을 수 있는 데이터로 바꾼다.
    .then(console.log)      //변환된 데이터를 콘솔에 출력한다. ==> 내 Task 목록을 확인할 수 있다.

fetch('/api/tasks/16', {  //서버에 PATCH /api/tasks/16 요청을 보낸다. ==> ID가 16인 Task를 수정한다.
    method: 'patch',      // HTTP 요청 메서드를 PATCH로 설정한다. ==> ID가 16인 Task를 수정한다.
    headers: { 'Content-Type': 'application/json' }, // 요청 헤더를 설정한다. ==> 서버에 JSON 데이터를 보낼 수 있도록 한다.
    body: JSON.stringify({ title: '라이딩 연습'}) // 요청 본문에 수정할 데이터를 JSON 문자열로 변환하여 설정한다. ==> ID가 16인 Task의 제목을 '라이딩 연습'으로 수정한다. 
})   .then(r => console.log(r.status))  //서버에서 받은 응답의 상태 코드를 콘솔에 출력한다. ==> 200이면 수정 성공, 404이면 해당 ID의 Task가 없음, 400이면 잘못된 요청임을 알 수 있다.
     


fetch('http://localhost:8000/tasks/16', {
    method: 'PATCH',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: '라이딩 연습', description: '' })
})
    .then(r => r.json().then(body => console.log(r.status, body)))










    allow pasting