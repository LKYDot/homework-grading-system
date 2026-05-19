import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type User } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(JSON.parse(localStorage.getItem('user') || 'null'))
  const token = ref<string | null>(localStorage.getItem('access_token'))

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  function setAuth(t: string, u: User) {
    token.value = t
    user.value = u
    localStorage.setItem('access_token', t)
    localStorage.setItem('user', JSON.stringify(u))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
  }

  async function login(username: string, password: string) {
    const { data } = await authApi.login({ username, password })
    setAuth(data.access_token, data.user)
    return data.user
  }

  async function register(
    username: string,
    email: string,
    password: string,
    fullName?: string,
  ) {
    const { data } = await authApi.register({
      username,
      email,
      password,
      full_name: fullName,
    })
    return data
  }

  return { user, token, isLoggedIn, isAdmin, setAuth, logout, login, register }
})
