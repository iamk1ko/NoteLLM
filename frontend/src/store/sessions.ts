import { defineStore } from 'pinia'
import type { ChatSession } from '@/services/sessions'

type SessionState = {
  sessions: ChatSession[]
  currentSession?: ChatSession
  loading: boolean
}

export const useSessionsStore = defineStore('sessions', {
  state: (): SessionState => ({
    sessions: [],
    currentSession: undefined,
    loading: false,
  }),
  actions: {
    setSessions(list: ChatSession[]) {
      this.sessions = list
    },
    setCurrent(session?: ChatSession) {
      this.currentSession = session
    },
    setLoading(value: boolean) {
      this.loading = value
    },
  },
})
