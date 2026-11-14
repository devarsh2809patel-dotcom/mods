export type Mode = 'auto' | 'pipeline' | 'iterative'
export type Review = { text: string; mode: 'pipeline' | 'iterative' }

declare module 'claude-code' {
  interface PluginState {
    promptmaster: {
      review: Review | null
      isBusy: boolean
      mode: Mode | 'default'
      turns: number
    }
  }
}
