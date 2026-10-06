# 0006. PC를 먼저 만들고 모바일은 Capacitor로 붙인다

- 상태: 채택. 모바일은 v1(Electron + Gemini), v2(Ollama) 다음에 한다
- 날짜: 2026-10-06

## 배경

학생들은 폰을 더 많이 쓴다. 하지만 Electron([0002](0002-desktop-with-electron.md))은 데스크톱 전용이다.

## 결정

**PC 버전을 먼저 만든다.**

- 이 프로젝트의 차별점("토큰이 어떤 서버도 지나가지 않는다", "민감 데이터는 로컬 모델")이 PC에서
  가장 잘 산다. 사용자 PC나 게이밍 노트북의 Ollama를 바로 쓸 수 있다
- 개발이 빠르다. 지금 React 화면을 그대로 쓰고 개발 맥에서 바로 확인한다
- 모바일은 KLAS+와 KLAS GPT가 이미 자리 잡고 있다. PC에서 먼저 쓸모를 보인다

**모바일은 나중에 Capacitor로 붙인다.** 같은 React 화면을 네이티브 앱 껍데기에 넣는다.
KLAS 로그인과 키 보관은 작은 네이티브 플러그인(Swift, Kotlin)으로 빼서 Electron main과 같은
경계를 지킨다. iPhone에서는 Apple Foundation Models를 로컬 모델로 쓸 수 있다. SwiftUI는 필요 없고,
모델을 부르는 플러그인만 Swift로 쓴다.

## PC 버전을 만들 때 지킬 것

모바일을 붙일 때 다시 짜지 않도록 처음부터 나눠 둔다.

```
packages/core (TypeScript, 플랫폼 무관)
 ├ 에이전트 루프, 도구 정의, 모델 제공자, 서버 API 클라이언트
 └ "기기 기능" 인터페이스: klasLogin, klasTasks, memories, ...
        ▲                          ▲
 Electron main (Node)        Capacitor 네이티브 플러그인
 safeStorage, SQLite          Keychain, Keystore, SQLite
```

- 에이전트 루프, 도구 정의, 모델 제공자는 Electron 코드와 섞지 않는다
- KLAS, 키 보관, 로컬 저장소는 "기기 기능" 인터페이스 뒤에 둔다

## 검토한 대안

- **React Native**: 네이티브 느낌이 가장 좋지만 화면을 새로 만들어야 한다
- **PWA**: 설치가 쉽지만 CORS 때문에 KLAS 호출에 프록시가 필요하다. [0001](0001-credentials-stay-on-device.md)과 충돌한다

## 결과

- 모바일은 어댑터 하나(Capacitor 플러그인)를 새로 짜는 일로 끝난다
- 모바일에서는 로컬 모델 선택지가 좁다. 지원 iPhone의 Apple Foundation Models 말고는 LLM 중계를
  기본으로 쓴다. 민감 도구를 끌 수 있는 설정을 둔다
- 앱스토어와 플레이스토어 심사가 필요하다
