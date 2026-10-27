<template>
  <div class="auth-page">
    <div class="auth-aside">
      <router-link to="/" class="brand" aria-label="十极 10G.HK 首页" title="十极 10G.HK">
        <BrandLogo size="auth" />
      </router-link>
      <h2>欢迎回来</h2>
      <p>登录控制台，管理您的 VPS 主机、公网对接服务与账单。</p>
      <ul>
        <li><el-icon><CircleCheckFilled /></el-icon> 全球节点自助选购</li>
        <li><el-icon><CircleCheckFilled /></el-icon> 服务与资源一站管理</li>
        <li><el-icon><CircleCheckFilled /></el-icon> 账单逐项透明可查</li>
      </ul>
    </div>

    <div class="auth-form-wrap">
      <div class="auth-card">
        <router-link to="/" class="brand-mobile" aria-label="十极 10G.HK 首页">
          <BrandLogo size="nav" />
        </router-link>
        <h1>登录账户</h1>
        <p class="sub">还没有账户？<router-link to="/register">免费注册 →</router-link></p>
        <el-alert
          v-if="sessionExpired"
          class="idle-alert"
          type="warning"
          :closable="false"
          show-icon
          title="登录已超时，请重新登录"
        />

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="onSubmit">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" size="large" placeholder="请输入用户名" :prefix-icon="User" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" size="large" show-password
                      placeholder="请输入密码" :prefix-icon="Lock" @keyup.enter="onSubmit" />
          </el-form-item>
          <el-button type="primary" size="large" round class="full" :loading="loading" @click="onSubmit">
            登录
          </el-button>
        </el-form>

        <router-link to="/" class="back">← 返回官网首页</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/store/auth'
import BrandLogo from '@/components/BrandLogo.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const formRef = ref(null)
const loading = ref(false)
const sessionExpired = computed(() => Boolean(route.query.expired))

onMounted(() => {
  if (sessionExpired.value) {
    ElMessage.warning('登录已超时，请重新登录')
  }
})
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onSubmit() {
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    await auth.fetchMe().catch(() => {})
    ElMessage.success('登录成功')
    router.push(route.query.redirect || '/console')
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: var(--ce-bg);
}
.auth-aside {
  background: radial-gradient(720px 480px at 25% 8%, #1e4e99, transparent 64%),
    linear-gradient(135deg, #0a1222, #102650);
  color: #fff;
  padding: clamp(40px, 7vw, 96px);
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.auth-aside .brand {
  display: inline-flex;
  align-items: center;
  margin-bottom: 40px;
}
.brand-mobile {
  display: none;
  margin-bottom: 18px;
}
.auth-aside h2 {
  font-size: 34px;
  margin: 0 0 14px;
}
.auth-aside p {
  color: #cbd5e1;
  font-size: 16px;
  line-height: 1.7;
  max-width: 380px;
}
.auth-aside ul {
  list-style: none;
  padding: 0;
  margin-top: 32px;
}
.auth-aside li {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  color: #e2e8f0;
}
.auth-aside li .el-icon {
  color: #34d399;
}
.auth-form-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
}
.auth-card {
  width: 100%;
  max-width: 400px;
  padding: 38px;
  border: 1px solid var(--ce-border);
  border-radius: var(--ce-radius-lg);
  background: var(--ce-surface);
  box-shadow: var(--ce-shadow);
}
.auth-card h1 {
  font-size: 30px;
  margin: 0 0 6px;
}
.sub {
  color: var(--ce-muted);
  margin: 0 0 16px;
}
.idle-alert {
  margin-bottom: 16px;
}
.sub a {
  color: var(--ce-primary);
  font-weight: 600;
}
.full {
  width: 100%;
  margin-top: 6px;
}
.back {
  display: block;
  text-align: center;
  margin-top: 24px;
  color: var(--ce-muted);
  font-size: 14px;
}
.back:hover {
  color: var(--ce-primary);
}
@media (max-width: 860px) {
  .auth-page {
    grid-template-columns: 1fr;
  }
  .auth-aside {
    display: none;
  }
  .brand-mobile {
    display: inline-flex;
  }
}
</style>
