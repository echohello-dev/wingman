import { Window } from 'happy-dom'

const window = new Window({ url: 'http://localhost:3000' })
Object.assign(globalThis, {
  window,
  document: window.document,
  navigator: window.navigator,
  HTMLElement: window.HTMLElement,
  MutationObserver: window.MutationObserver,
  IS_REACT_ACT_ENVIRONMENT: true,
})
