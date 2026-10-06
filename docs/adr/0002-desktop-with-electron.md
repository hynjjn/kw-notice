# 0002. 데스크톱 앱은 Electron으로 만든다

- 상태: 채택
- 날짜: 2026-10-06

## 배경

[0001](0001-credentials-stay-on-device.md)에 따라 KLAS 호출과 비밀 보관은 사용자 기기에서 해야
한다. 지금 프론트는 브라우저 SPA라 KLAS에 직접 요청하지 못하고(CORS), OS 키체인에도 닿지 못한다.

필요한 것은 **웹뷰와 분리된, 권한 있는 프로세스**다. 웹뷰는 공지 본문 HTML, 첨부 미리보기,
모델이 만든 마크다운처럼 외부 내용을 그린다. 여기서 스크립트가 끼어드는 사고가 나도 비밀에는
닿지 못해야 한다.

## 결정

**Electron으로 데스크톱 앱을 만든다.** 지금 React 화면을 renderer에서 그대로 쓰고,
KLAS, 키 보관, SQLite는 main process(TypeScript)에 둔다.

- 키 보관은 Electron 내장 `safeStorage`(OS 키체인)를 쓴다
- renderer는 `contextIsolation`과 `sandbox`를 켜고, preload가 노출한 정해진 IPC만 쓴다
- KLAS 로직은 "기기 기능" 인터페이스 뒤에 둔다. Electron main은 그 구현 중 하나다
  ([0006](0006-pc-first-mobile-later.md))

## 검토한 대안

| | 장점 | 단점 |
| --- | --- | --- |
| Tauri | 앱이 수 MB로 가볍다. React 재사용 | 권한 있는 층이 Rust다. 플러그인을 JS에서 쓰면 Rust를 줄일 수 있지만 토큰이 웹뷰를 지나가 분리 이점이 약해진다 |
| React Native | 모바일에 맞다 | 화면을 새로 만들어야 한다. 로컬 모델을 PC에서 돌리는 계획과 따로 논다 |
| 브라우저 확장 | 사용자의 KLAS 세션을 그대로 써서 비밀번호를 아예 다루지 않는다 | 로컬 모델 연결, 로컬 저장소가 제한적이다 |
| 웹앱 | 설치가 없다 | CORS 때문에 프록시 서버가 필요하다. 0001과 충돌한다 |

Electron을 고른 이유는 언어다. 권한 있는 층을 익숙한 TypeScript로 쓸 수 있어서 가장 빨리
만들고 검증할 수 있다. 보안 경계(웹뷰와 main 분리)는 Tauri와 같다.

## 결과

얻는 것

- React 화면과 TypeScript 코드를 그대로 쓴다
- KLAS 호출에 프록시가 필요 없다. 토큰이 어떤 서버도 지나가지 않는다
- 로컬 모델(Ollama, node-llama-cpp)을 main이나 별도 프로세스에서 붙이기 쉽다

잃는 것

- 앱이 무겁다(100MB 이상, Chromium 포함). 메모리도 많이 쓴다
- 배포 일이 생긴다. macOS 서명과 공증(Apple Developer 계정, 연 99달러), Windows 서명,
  자동 업데이트가 필요하다
- 사용자 앱 버전이 제각각이 된다. 서버 API는 하위 호환을 지키거나 버전을 붙인다

나중에 가벼운 앱이 필요하면 Tauri로 옮길 수 있다. React 화면, `packages/core`, 서버는 그대로이고
main의 구현만 바뀐다.
