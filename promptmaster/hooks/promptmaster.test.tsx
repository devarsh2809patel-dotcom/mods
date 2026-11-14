import { expect, test } from 'claude-code/testing'

import { pickMode } from './register'

const LONG =
  'i need a report on our sales for q3, include charts, and also a summary for the boss, and maybe a spreadsheet with the raw numbers. it should look professional. also compare with last year. the boss likes short stuff but also wants details'
const SHORT = 'make the login button blue'

test('auto mode: long -> pipeline, short follow-up -> iterative', () => {
  expect(pickMode(LONG, 0)).toBe('pipeline')
  expect(pickMode(LONG, 5)).toBe('pipeline')
  expect(pickMode(SHORT, 3)).toBe('iterative')
  expect(pickMode(SHORT, 0)).toBe('pipeline')
})

const BAND = {
  plugin: 'promptmaster',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false, isCollapsed: false, isWorking: false, maxRows: 10, bodyColumns: 80,
    scroll: { offset: 0, bodyRows: 8 }, view: {},
  },
} as const

for (const [name, draft, presses, has, hasNot] of [
  ['long sample, auto -> pipeline template', LONG, 0, 'Deliverables:', 'Scope:'],
  ['short sample, forced iterative template', SHORT, 2, 'Scope:', 'Deliverables:'],
] as const) {
  test(name, async ($, on) => {
    let sent: any
    let filled: any
    on('prompt.read', () => ({ value: { text: draft, cursor: 0 } }))
    on('model.complete', (_, e) => {
      sent = e
      return { value: { isAnswered: true, text: 'Goal: x', usage: {} as any } }
    })
    on('prompt.fill', (_, e) => {
      filled = e
      return { isFilled: true, text: e.text, cursor: e.cursor ?? 0 } as any
    })
    on('ui.toast', () => ({ value: undefined }) as any)
    on('prompt.submit', () => {
      throw new Error('must never auto-send')
    })

    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({ ...BAND, surface })
      if (surface === 'terminal') for (let i = 0; i < presses; i++) await ui.press({ key: 'mode' })
      await ui.press({ key: 'run' })
      expect(sent.system).toContain('NEVER answer')
      expect(sent.system).toContain(has)
      expect(sent.system).not.toContain(hasNot)
      expect(sent.prompt).toContain(draft)
      // the result is shown for review, and Use it fills the box without sending
      expect(await ui.find({ key: 'use' })).toBeTruthy()
      expect(await ui.find({ key: 'edit' })).toBeTruthy()
      await ui.press({ key: 'use' })
      expect(filled.text).toBe('Goal: x')
      await ui.unmount()
    }
  })
}
