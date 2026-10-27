<template>
  <div class="auth-page">
    <div class="auth-aside">
      <router-link to="/" class="brand" aria-label="十极 10G.HK 首页" title="十极 10G.HK">
        <BrandLogo size="auth" />
      </router-link>
      <h2>创建您的账户</h2>
      <p>注册即可浏览全部节点与套餐，下单后由专属团队为您快速开通。</p>
      <ul>
        <li><el-icon><CircleCheckFilled /></el-icon> 免费注册，无需预付</li>
        <li><el-icon><CircleCheckFilled /></el-icon> 多区域节点任您选择</li>
        <li><el-icon><CircleCheckFilled /></el-icon> 自助控制台即开即用</li>
      </ul>
    </div>

    <div class="auth-form-wrap">
      <div class="auth-card">
        <router-link to="/" class="brand-mobile" aria-label="十极 10G.HK 首页">
          <BrandLogo size="nav" />
        </router-link>
        <h1>注册账户</h1>
        <p class="sub">已有账户？<router-link to="/login">直接登录 →</router-link></p>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-form-item label="账户类型" prop="customer_type">
            <el-radio-group v-model="form.customer_type">
              <el-radio-button label="personal">个人</el-radio-button>
              <el-radio-button label="enterprise">企业</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <div class="row2">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" placeholder="登录用户名" :prefix-icon="User" />
            </el-form-item>
            <el-form-item label="联系人" prop="contact_name">
              <el-input v-model="form.contact_name" placeholder="您的称呼" />
            </el-form-item>
          </div>
          <div class="row2">
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="form.email" placeholder="name@example.com" :prefix-icon="Message" />
            </el-form-item>
            <el-form-item label="手机" prop="contact_phone">
              <el-input v-model="form.contact_phone" placeholder="选填" />
            </el-form-item>
          </div>
          <el-form-item v-if="form.customer_type === 'enterprise'" label="公司名称" prop="company_name">
            <el-input v-model="form.company_name" placeholder="企业全称" />
          </el-form-item>
          <el-form-item label="推广优惠码">
            <el-input v-model="form.promotion_code" placeholder="选填，填写渠道提供的推荐码可享专属优惠" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" show-password placeholder="至少 8 位" :prefix-icon="Lock" />
            <div class="password-tip">至少 8 位，不能使用纯数字或过于常见的密码。</div>
          </el-form-item>
          <el-button type="primary" size="large" round class="full" :loading="loading" @click="onSubmit">
            注册并登录
          </el-button>
        </el-form>

        <router-link to="/" class="back">← 返回官网首页</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, Message, User } from '@element-plus/icons-vue'
import { register } from '@/api'
import { useAuthStore } from '@/store/auth'
import BrandLogo from '@/components/BrandLogo.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const formRef = ref(null)
const loading = ref(false)
const form = reactive({
  customer_type: 'personal',
  username: '', contact_name: '', email: '', contact_phone: '',
  company_name: '', promotion_code: String(route.query.promo || route.query.ref || ''),
  password: '',
})
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  contact_name: [{ required: true, message: '请输入联系人', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (String(value || '').length < 8) callback(new Error('密码至少 8 位'))
        else if (/^\d+$/.test(value)) callback(new Error('密码不能只包含数字'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function onSubmit() {
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return
  loading.value = true
  try {
    const res = await register({ ...form })
    const data = res.data || res
    auth.setTokens(data.access, data.refresh)
    auth.user = data.user
    const promotion = data.promotion
    ElMessage.success(
      promotion
        ? `注册成功，已绑定推广码 ${promotion.promotion_code}，享 ${promotion.promotion_discount_rate}% 优惠`
        : '注册成功，已自动登录',
    )
    router.push('/console')
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
  max-width: 480px;
  padding: 36px;
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
  margin: 0 0 22px;
}
.sub a {
  color: var(--ce-primary);
  font-weight: 600;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.full {
  width: 100%;
  margin-top: 6px;
}
.password-tip {
  color: var(--ce-muted);
  font-size: 12px;
  line-height: 1.5;
  margin-top: 4px;
}
.back {
  display: block;
  text-align: center;
  margin-top: 20px;
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
  .row2 {
    grid-template-columns: 1fr;
  }
}
</style>
