<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const fullName = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  if (!username.value || !email.value || !password.value) {
    error.value = '请填写所有必填项'
    return
  }
  if (password.value !== confirmPassword.value) {
    error.value = '两次密码不一致'
    return
  }
  if (password.value.length < 6) {
    error.value = '密码长度至少6位'
    return
  }
  loading.value = true
  try {
    await auth.register(username.value, email.value, password.value, fullName.value)
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <h2>注册</h2>
      <p class="auth-subtitle">创建新账号</p>

      <div v-if="error" class="error-message" role="alert">{{ error }}</div>

      <form @submit.prevent="handleRegister" novalidate>
        <div class="form-group">
          <label class="form-label" for="reg-username">用户名 *</label>
          <input id="reg-username" v-model="username" class="form-input" placeholder="请输入用户名" required />
        </div>
        <div class="form-group">
          <label class="form-label" for="reg-email">邮箱 *</label>
          <input id="reg-email" v-model="email" class="form-input" type="email" placeholder="请输入邮箱" required />
        </div>
        <div class="form-group">
          <label class="form-label" for="reg-name">姓名</label>
          <input id="reg-name" v-model="fullName" class="form-input" placeholder="请输入姓名（选填）" />
        </div>
        <div class="form-group">
          <label class="form-label" for="reg-password">密码 *</label>
          <input id="reg-password" v-model="password" class="form-input" type="password" placeholder="至少6位" required />
        </div>
        <div class="form-group">
          <label class="form-label" for="reg-confirm">确认密码 *</label>
          <input id="reg-confirm" v-model="confirmPassword" class="form-input" type="password" placeholder="请再次输入密码" required />
        </div>
        <button class="btn btn-primary btn-block" :disabled="loading" type="submit" aria-label="注册">
          <span v-if="loading" class="spinner" aria-hidden="true"></span>
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <p class="auth-link">
        已有账号？<router-link to="/login">立即登录</router-link>
      </p>
    </div>
  </div>
</template>
