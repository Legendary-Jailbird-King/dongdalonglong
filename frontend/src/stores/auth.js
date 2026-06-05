import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  // ── 状态 ──────────────────────────────────────────────
  const token = ref(localStorage.getItem('token') || '')
  const role = ref(localStorage.getItem('role') || '')
  const userId = ref(Number(localStorage.getItem('userId')) || 0)
  const userName = ref(localStorage.getItem('userName') || '')

  // ── 计算属性 ────────────────────────────────────────────
  const isLoggedIn = computed(() => !!token.value)

  // ── 方法 ──────────────────────────────────────────────
  function setAuth(data) {
    token.value = data.access_token
    role.value = data.role
    userId.value = data.user_id
    userName.value = data.user_name

    localStorage.setItem('token', data.access_token)
    localStorage.setItem('role', data.role)
    localStorage.setItem('userId', String(data.user_id))
    localStorage.setItem('userName', data.user_name)
  }

  function logout() {
    token.value = ''
    role.value = ''
    userId.value = 0
    userName.value = ''

    localStorage.removeItem('token')
    localStorage.removeItem('role')
    localStorage.removeItem('userId')
    localStorage.removeItem('userName')
  }

  return { token, role, userId, userName, isLoggedIn, setAuth, logout }
})
