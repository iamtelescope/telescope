import { defineStore } from 'pinia'

import { useGetCurrentUser } from '@/composables/auth/useAuthService'

export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null, isLoggedIn: undefined, error: null }),

  actions: {
    async login() {
      const { user, error, load } = useGetCurrentUser()
      await load()
      if (!error.value) {
        this.user = user
        this.isLoggedIn = true
        return null
      } else {
        this.isLoggedIn = false
        this.user = null
        this.error = error
        return error.value
      }
    },
  }
})