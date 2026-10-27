<template>
  <div class="profile" v-loading="loading">
    <div class="cols">
      <div class="ce-card panel">
        <h3>客户资料</h3>
        <el-descriptions :column="1" border style="margin:14px 0 20px">
          <el-descriptions-item label="客户编号">{{ profile.customer_no }}</el-descriptions-item>
          <el-descriptions-item label="登录账号">{{ profile.username }}</el-descriptions-item>
          <el-descriptions-item label="客户类型">{{ profile.customer_type_label }}</el-descriptions-item>
          <el-descriptions-item label="账户状态">
            <el-tag size="small">{{ profile.status_label }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="账户余额">
            {{ money(profile.balance) }}
            <el-button
              v-if="caps.billing_pay"
              link
              type="primary"
              @click="router.push('/console/bills?recharge=1')"
            >充值</el-button>
          </el-descriptions-item>
          <el-descriptions-item label="信用额度">{{ money(profile.credit_limit) }}</el-descriptions-item>
          <el-descriptions-item v-if="profile.reputation_visible" label="信誉值">
            {{ profile.reputation_balance }} / {{ profile.reputation_quota }}
            <span class="muted">（{{ profile.reputation_mode === 'monthly' ? '按月更新' : '一次性' }}）</span>
          </el-descriptions-item>
        </el-descriptions>

        <el-form :model="form" label-position="top">
          <div class="row2">
            <el-form-item label="客户/公司名称">
              <el-input v-model="form.name" :disabled="!caps.profile_update" />
            </el-form-item>
            <el-form-item label="联系人">
              <el-input v-model="form.contact_name" :disabled="!caps.profile_update" />
            </el-form-item>
          </div>
          <div class="row2">
            <el-form-item label="联系电话">
              <el-input v-model="form.contact_phone" :disabled="!caps.profile_update" />
            </el-form-item>
            <el-form-item label="联系邮箱">
              <el-input v-model="form.contact_email" :disabled="!caps.profile_update" />
            </el-form-item>
          </div>
          <div class="row2">
            <el-form-item label="省份">
              <el-input v-model="form.province" :disabled="!caps.profile_update" />
            </el-form-item>
            <el-form-item label="城市">
              <el-input v-model="form.city" :disabled="!caps.profile_update" />
            </el-form-item>
          </div>
          <el-form-item label="详细地址">
            <el-input v-model="form.address" :disabled="!caps.profile_update" />
          </el-form-item>
          <el-button v-if="caps.profile_update" type="primary" :loading="saving" @click="save">保存资料</el-button>
        </el-form>
      </div>

      <div class="ce-card panel">
        <h3>修改密码</h3>
        <el-form ref="pwdRef" :model="pwd" :rules="pwdRules" label-position="top" style="margin-top:14px">
          <el-form-item label="当前密码" prop="old_password">
            <el-input v-model="pwd.old_password" type="password" show-password :prefix-icon="Lock" />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="pwd.new_password" type="password" show-password :prefix-icon="Lock" />
          </el-form-item>
          <el-form-item label="确认新密码" prop="confirm_password">
            <el-input v-model="pwd.confirm_password" type="password" show-password :prefix-icon="Lock" />
          </el-form-item>
          <el-button type="primary" :loading="changing" @click="doChangePwd">更新密码</el-button>
        </el-form>

        <el-alert type="info" :closable="false" show-icon style="margin-top:20px"
                  title="修改密码后，下次登录请使用新密码。" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import { changePassword, getProfile, updateProfile } from '@/api'
import { useAuthStore } from '@/store/auth'
import { useCapabilities } from '@/composables/useCapabilities'
import { money } from '@/utils/format'

const auth = useAuthStore()
const { caps } = useCapabilities()
const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const changing = ref(false)
const profile = ref({})
const form = reactive({
  name: '', contact_name: '', contact_phone: '', contact_email: '',
  province: '', city: '', address: '',
})
const pwdRef = ref(null)
const pwd = reactive({ old_password: '', new_password: '', confirm_password: '' })
const pwdRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [{ required: true, min: 8, message: '新密码至少 8 位', trigger: 'blur' }],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (r, v, cb) => (v === pwd.new_password ? cb() : cb(new Error('两次密码不一致'))),
      trigger: 'blur',
    },
  ],
}

async function load() {
  loading.value = true
  try {
    const res = await getProfile()
    profile.value = res.data || res
    Object.assign(form, {
      name: profile.value.name || '',
      contact_name: profile.value.contact_name || '',
      contact_phone: profile.value.contact_phone || '',
      contact_email: profile.value.contact_email || '',
      province: profile.value.province || '',
      city: profile.value.city || '',
      address: profile.value.address || '',
    })
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await updateProfile({ ...form })
    ElMessage.success('资料已更新')
    load()
  } catch (e) {
    /* 拦截器提示 */
  } finally {
    saving.value = false
  }
}

async function doChangePwd() {
  const ok = await pwdRef.value.validate().catch(() => false)
  if (!ok) return
  changing.value = true
  try {
    await changePassword({ ...pwd })
    ElMessage.success('密码已修改，请重新登录')
    auth.logout()
    router.push('/login')
  } catch (e) {
    /* 拦截器提示 */
  } finally {
    changing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.cols {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 18px;
  align-items: start;
}
.panel {
  padding: 24px;
}
.panel h3 {
  margin: 0;
  font-size: 17px;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
@media (max-width: 980px) {
  .cols {
    grid-template-columns: 1fr;
  }
}
</style>
