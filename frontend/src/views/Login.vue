<template>
  <div class="login-bg">
    <!-- 装饰粒子 -->
    <div class="particles">
      <span v-for="i in 20" :key="i" class="dot" :style="dotStyle(i)" />
    </div>

    <div class="login-card">
      <div class="card-left">
        <div class="brand">
          <div class="brand-icon">🍔</div>
          <h1>外卖管理系统</h1>
          <p>Takeaway Management System</p>
        </div>
        <div class="features">
          <div class="feat"><span>📋</span> 智能下单</div>
          <div class="feat"><span>🔔</span> 实时推送</div>
          <div class="feat"><span>🛵</span> 骑手抢单</div>
        </div>
      </div>

      <div class="card-right">
        <h2>{{ isLogin ? '欢迎回来' : '创建账户' }}</h2>
        <p class="subtitle">{{ isLogin ? '登录您的账户继续使用' : '注册后即可开始点餐接单' }}</p>

        <!-- 角色选择 -->
        <div class="role-tabs">
          <button
            :class="['role-btn', { active: form.role === 'customer' }]"
            @click="form.role = 'customer'"
          >👤 顾客</button>
          <button
            :class="['role-btn', { active: form.role === 'merchant' }]"
            @click="form.role = 'merchant'"
          >🏪 商家</button>
          <button
            :class="['role-btn', { active: form.role === 'courier' }]"
            @click="form.role = 'courier'"
          >🛵 骑手</button>
        </div>

        <!-- 表单 -->
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large">
          <el-form-item label="用户名" prop="name">
            <el-input
              v-model="form.name"
              placeholder="请输入用户名"
              :prefix-icon="User"
              class="custom-input"
            />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              show-password
              class="custom-input"
              @keyup.enter="handleSubmit"
            />
          </el-form-item>
        </el-form>

        <el-button
          type="primary"
          size="large"
          :loading="loading"
          class="submit-btn"
          @click="handleSubmit"
        >
          {{ isLogin ? '登 录' : '注 册' }}
        </el-button>

        <div class="toggle-mode">
          {{ isLogin ? '还没有账户？' : '已有账户？' }}
          <el-link type="primary" @click="isLogin = !isLogin">
            {{ isLogin ? '立即注册' : '去登录' }}
          </el-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { loginAPI, registerAPI } from '../api/services'

const router = useRouter()
const auth = useAuthStore()

const isLogin = ref(true)
const loading = ref(false)
const formRef = ref(null)

const form = reactive({
  role: 'customer',
  name: '',
  password: '',
})

// 切换角色时清空表单
watch(() => form.role, () => {
  form.name = ''
  form.password = ''
  formRef.value?.clearValidate()
})

const rules = {
  name: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 4, message: '密码至少4位', trigger: 'blur' },
  ],
}

const roleRoutes = { customer: '/customer', merchant: '/merchant', courier: '/courier' }

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const api = isLogin.value ? loginAPI : registerAPI
    const res = await api({ ...form })

    if (isLogin.value) {
      auth.setAuth(res.data)
      ElMessage.success(`欢迎回来，${res.data.user_name}！`)
      router.push(roleRoutes[res.data.role])
    } else {
      ElMessage.success('注册成功，请登录')
      isLogin.value = true
    }
  } catch {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}

function dotStyle(i) {
  const size = 4 + Math.random() * 8
  return {
    left: Math.random() * 100 + '%',
    top: Math.random() * 100 + '%',
    width: size + 'px',
    height: size + 'px',
    animationDelay: Math.random() * 6 + 's',
    animationDuration: 3 + Math.random() * 4 + 's',
  }
}
</script>

<style scoped>
.login-bg {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
  position: relative;
  overflow: hidden;
  padding: 20px;
}

/* ── 浮动粒子 ── */
.particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.dot {
  position: absolute;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 50%;
  animation: floatUp 5s infinite ease-in;
}
@keyframes floatUp {
  0%, 100% { transform: translateY(0); opacity: 0.3; }
  50% { transform: translateY(-30px); opacity: 0.8; }
}

/* ── 卡片 ── */
.login-card {
  display: flex;
  width: 780px;
  max-width: 100%;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 25px 80px rgba(0, 0, 0, 0.4);
  z-index: 1;
}

/* ── 左侧品牌 ── */
.card-left {
  flex: 0 0 44%;
  background: linear-gradient(160deg, #667eea, #764ba2);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px 36px;
  color: #fff;
}
.brand-icon {
  font-size: 52px;
  margin-bottom: 16px;
}
.brand h1 {
  font-size: 26px;
  font-weight: 700;
  margin-bottom: 6px;
}
.brand p {
  font-size: 13px;
  opacity: 0.75;
  letter-spacing: 2px;
}
.features {
  margin-top: 36px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.feat {
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  opacity: 0.9;
}
.feat span { font-size: 20px; }

/* ── 右侧表单 ── */
.card-right {
  flex: 1;
  padding: 48px 40px;
  background: #fff;
}
.card-right h2 {
  font-size: 24px;
  color: #1a1a2e;
  margin-bottom: 4px;
}
.subtitle {
  color: #999;
  font-size: 13px;
  margin-bottom: 24px;
}

.role-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}
.role-btn {
  flex: 1;
  padding: 10px 0;
  border: 2px solid #e8e8e8;
  border-radius: 10px;
  background: #fafafa;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.25s;
  color: #666;
}
.role-btn:hover { border-color: #c0c0f0; background: #f5f5ff; }
.role-btn.active {
  border-color: #667eea;
  background: linear-gradient(135deg, #667eea15, #764ba215);
  color: #667eea;
  font-weight: 600;
}

.custom-input :deep(.el-input__wrapper) {
  border-radius: 10px;
  transition: all 0.25s;
}
.custom-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c0c0f0;
}

.submit-btn {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: none;
  margin-top: 4px;
}
.submit-btn:hover {
  background: linear-gradient(135deg, #5a6fd6, #6a4192);
}

.toggle-mode {
  text-align: center;
  margin-top: 20px;
  font-size: 13px;
  color: #999;
}

/* 移动端适配 */
@media (max-width: 640px) {
  .login-card { flex-direction: column; }
  .card-left { padding: 28px 24px; }
  .features { display: none; }
  .card-right { padding: 28px 24px; }
}
</style>
