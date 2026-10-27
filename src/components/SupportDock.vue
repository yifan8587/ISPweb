<template>
  <aside class="support-dock" aria-label="客户支持">
    <button class="dock-primary" type="button" @click="openInquiry('help')">需要帮助</button>
    <button class="dock-outline" type="button" @click="openInquiry('trial')">申请测试</button>
    <button class="dock-icon" type="button" aria-label="在线客服" title="在线客服" @click="openContactDialog">
      <el-icon><Service /></el-icon>
    </button>
  </aside>

  <el-dialog v-model="inquiryVisible" :title="inquiryType === 'trial' ? '申请测试' : '需要帮助'" width="520px" destroy-on-close>
    <p class="dialog-intro">留下您的需求与联系方式，服务团队会尽快与您联系。</p>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <div class="form-grid">
        <el-form-item label="联系人" prop="contact_name"><el-input v-model="form.contact_name" placeholder="您的称呼" /></el-form-item>
        <el-form-item label="公司/组织"><el-input v-model="form.company_name" placeholder="选填" /></el-form-item>
      </div>
      <div class="form-grid">
        <el-form-item label="联系电话" prop="phone"><el-input v-model="form.phone" placeholder="手机号或座机" /></el-form-item>
        <el-form-item label="联系邮箱" prop="email"><el-input v-model="form.email" placeholder="name@example.com" /></el-form-item>
      </div>
      <el-form-item label="偏好联系方式"><el-radio-group v-model="form.preferred_contact"><el-radio-button label="电话" /><el-radio-button label="微信" /><el-radio-button label="邮箱" /></el-radio-group></el-form-item>
      <el-form-item :label="inquiryType === 'trial' ? '测试需求' : '需求内容'" prop="requirements">
        <el-input v-model="form.requirements" type="textarea" :rows="4" :placeholder="inquiryType === 'trial' ? '请说明测试业务、预期区域、资源规格等' : '请描述您需要的帮助'" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="inquiryVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submitInquiry">提交需求</el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="contactVisible"
    title="在线客服"
    width="480px"
    align-center
    destroy-on-close
    class="contact-dialog"
  >
    <p class="contact-intro">选择以下方式添加客服账号，即可开始在线沟通。</p>

    <div v-loading="contactLoading" class="contact-list">
      <div v-if="contact.qq" class="contact-card qq">
        <div class="contact-head">
          <span class="contact-badge">QQ</span>
          <strong>添加 QQ 客服</strong>
        </div>
        <div class="contact-account">{{ contact.qq }}</div>
        <p class="contact-tip">复制号码后在 QQ 中搜索添加，或点击下方直接发起会话。</p>
        <div class="contact-actions">
          <el-button size="small" @click="copyText(contact.qq, 'QQ 号已复制')">复制 QQ 号</el-button>
          <el-button size="small" type="primary" plain @click="openQqChat(contact.qq)">打开 QQ 会话</el-button>
        </div>
      </div>

      <div v-if="contact.wechat || contact.wechat_qr" class="contact-card wechat">
        <div class="contact-head">
          <span class="contact-badge">微信</span>
          <strong>添加微信客服</strong>
        </div>
        <img
          v-if="contact.wechat_qr"
          :src="contact.wechat_qr"
          alt="微信客服二维码"
          class="contact-qr"
        />
        <div v-if="contact.wechat" class="contact-account">{{ contact.wechat }}</div>
        <p class="contact-tip">
          {{ contact.wechat_qr ? '使用微信扫一扫上方二维码，或搜索微信号添加好友。' : '复制微信号后在微信中搜索添加。' }}
        </p>
        <div v-if="contact.wechat" class="contact-actions">
          <el-button size="small" @click="copyText(contact.wechat, '微信号已复制')">复制微信号</el-button>
        </div>
      </div>

      <div v-if="contact.telegram" class="contact-card telegram">
        <div class="contact-head">
          <span class="contact-badge">TG</span>
          <strong>Telegram 客服</strong>
        </div>
        <div class="contact-account">{{ telegramDisplay }}</div>
        <p class="contact-tip">点击下方打开 Telegram 添加客服或发起私聊。</p>
        <div class="contact-actions">
          <el-button size="small" @click="copyText(contact.telegram, 'Telegram 已复制')">复制账号</el-button>
          <el-button size="small" type="primary" plain @click="openTelegram(contact.telegram)">打开 Telegram</el-button>
        </div>
      </div>

      <div v-if="contact.email" class="contact-card email">
        <div class="contact-head">
          <span class="contact-badge">邮箱</span>
          <strong>客服邮箱</strong>
        </div>
        <div class="contact-account">{{ contact.email }}</div>
        <p class="contact-tip">发送邮件说明需求，我们会尽快回复。</p>
        <div class="contact-actions">
          <el-button size="small" @click="copyText(contact.email, '邮箱已复制')">复制邮箱</el-button>
          <el-button size="small" type="primary" plain @click="openMail(contact.email)">写邮件</el-button>
        </div>
      </div>

      <div v-if="contact.phone" class="contact-card phone">
        <div class="contact-head">
          <span class="contact-badge">电话</span>
          <strong>客服电话</strong>
        </div>
        <div class="contact-account">{{ contact.phone }}</div>
        <p class="contact-tip">工作时间可拨打，或复制号码后联系。</p>
        <div class="contact-actions">
          <el-button size="small" @click="copyText(contact.phone, '电话已复制')">复制电话</el-button>
          <el-button size="small" type="primary" plain @click="openTel(contact.phone)">拨打电话</el-button>
        </div>
      </div>

      <div v-if="contact.wecom_kf_url" class="contact-card wecom">
        <div class="contact-head">
          <span class="contact-badge">企微</span>
          <strong>企业微信客服</strong>
        </div>
        <img v-if="wecomQr" :src="wecomQr" alt="企业微信客服二维码" class="contact-qr" />
        <p class="contact-tip">使用微信扫描企业微信客服二维码，或打开客服入口。</p>
        <div class="contact-actions">
          <el-button size="small" type="primary" plain @click="openWecomLink">打开客服入口</el-button>
        </div>
      </div>

      <el-empty
        v-if="!contactLoading && !hasAnyContact"
        description="客服账号暂未配置，请通过「需要帮助」提交需求，我们会尽快联系您。"
        :image-size="72"
      />
    </div>

    <template #footer>
      <el-button @click="contactVisible = false">关闭</el-button>
      <el-button type="primary" plain @click="openInquiryFromContact">留言给我们</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import QRCode from 'qrcode'
import { ElMessage } from 'element-plus'
import { createSupportInquiry, getSupportConfig } from '@/api'

const inquiryVisible = ref(false)
const contactVisible = ref(false)
const contactLoading = ref(false)
const inquiryType = ref('help')
const submitting = ref(false)
const formRef = ref()
const wecomQr = ref('')

const contact = reactive({
  qq: '',
  wechat: '',
  wechat_qr: '',
  telegram: '',
  wecom_kf_url: '',
  email: '',
  phone: '',
})

const form = reactive({
  contact_name: '', company_name: '', phone: '', email: '',
  preferred_contact: '电话', requirements: '',
})
const rules = {
  contact_name: [{ required: true, message: '请填写联系人', trigger: 'blur' }],
  requirements: [{ required: true, message: '请填写需求内容', trigger: 'blur' }],
}

const hasAnyContact = computed(() =>
  contact.qq || contact.wechat || contact.wechat_qr || contact.telegram
  || contact.wecom_kf_url || contact.email || contact.phone
)

const telegramDisplay = computed(() => {
  const raw = (contact.telegram || '').trim()
  if (!raw) return ''
  if (raw.startsWith('http')) return raw.replace(/^https?:\/\/(www\.)?t\.me\//i, '@')
  return raw.startsWith('@') ? raw : `@${raw}`
})

function openInquiry(type) {
  inquiryType.value = type
  inquiryVisible.value = true
}

function openInquiryFromContact() {
  contactVisible.value = false
  openInquiry('help')
}

async function loadSupportConfig() {
  contactLoading.value = true
  try {
    const config = await getSupportConfig()
    contact.qq = (config.qq || '').trim()
    contact.wechat = (config.wechat || '').trim()
    contact.wechat_qr = (config.wechat_qr || '').trim()
    contact.telegram = (config.telegram || '').trim()
    contact.wecom_kf_url = (config.wecom_kf_url || '').trim()
    contact.email = (config.email || '').trim()
    contact.phone = (config.phone || '').trim()
    wecomQr.value = ''
    if (contact.wecom_kf_url) {
      wecomQr.value = await QRCode.toDataURL(contact.wecom_kf_url, { width: 200, margin: 1 })
    }
  } catch {
    ElMessage.error('暂时无法获取客服信息')
  } finally {
    contactLoading.value = false
  }
}

async function openContactDialog() {
  contactVisible.value = true
  await loadSupportConfig()
}

async function copyText(text, okMsg) {
  const value = (text || '').trim()
  if (!value) return
  try {
    await navigator.clipboard.writeText(value)
    ElMessage.success(okMsg)
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}

function openQqChat(qq) {
  const num = String(qq || '').replace(/\D/g, '')
  if (!num) return
  window.open(`https://wpa.qq.com/msgrd?v=3&uin=${num}&site=qq&menu=yes`, '_blank', 'noopener,noreferrer')
}

function telegramUrl(raw) {
  const value = (raw || '').trim()
  if (!value) return ''
  if (/^https?:\/\//i.test(value)) return value
  const username = value.replace(/^@/, '')
  return `https://t.me/${username}`
}

function openTelegram(raw) {
  const url = telegramUrl(raw)
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

function openWecomLink() {
  if (contact.wecom_kf_url) {
    window.open(contact.wecom_kf_url, '_blank', 'noopener,noreferrer')
  }
}

function openMail(email) {
  const value = (email || '').trim()
  if (value) window.open(`mailto:${value}`, '_self')
}

function openTel(phone) {
  const value = String(phone || '').replace(/[^\d+]/g, '')
  if (value) window.open(`tel:${value}`, '_self')
}

async function submitInquiry() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  if (!form.phone && !form.email) {
    ElMessage.warning('请至少填写联系电话或联系邮箱')
    return
  }
  submitting.value = true
  try {
    const res = await createSupportInquiry({
      ...form,
      inquiry_type: inquiryType.value,
      source_url: window.location.href,
    })
    ElMessage.success(`${res.detail || '需求已提交'}（编号：${res.inquiry_no}）`)
    inquiryVisible.value = false
    Object.assign(form, { contact_name: '', company_name: '', phone: '', email: '', preferred_contact: '电话', requirements: '' })
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.support-dock { position: fixed; z-index: 90; right: 18px; top: 50%; display: grid; gap: 10px; transform: translateY(-50%); }
.support-dock button { width: 52px; min-height: 86px; border-radius: 26px; cursor: pointer; writing-mode: vertical-rl; letter-spacing: 0.12em; font-weight: 750; transition: transform .2s, box-shadow .2s; }
.support-dock button:hover { transform: translateY(-2px); }
.dock-primary { border: 0; background: linear-gradient(160deg, #22c55e, #06b6d4); color: #fff; box-shadow: 0 12px 24px rgba(6, 182, 212, .22); }
.dock-outline { border: 1px solid #22c55e; background: #fff; color: #0f9f6e; }
.dock-icon { min-height: 48px !important; border: 1px solid var(--ce-border); background: #fff; color: var(--ce-primary); box-shadow: var(--ce-shadow); writing-mode: initial !important; letter-spacing: 0 !important; }
.dock-icon .el-icon { font-size: 22px; }
.dialog-intro,
.contact-intro {
  margin: 0 0 16px;
  color: var(--ce-muted);
  font-size: 14px;
  line-height: 1.6;
}
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.contact-list { display: grid; gap: 12px; min-height: 80px; }
.contact-card {
  border: 1px solid var(--ce-border);
  border-radius: 14px;
  padding: 14px 16px;
  background: linear-gradient(180deg, #fff 0%, #f8fafc 100%);
}
.contact-card.qq { border-color: #bfdbfe; background: linear-gradient(180deg, #eff6ff 0%, #fff 100%); }
.contact-card.wechat { border-color: #bbf7d0; background: linear-gradient(180deg, #f0fdf4 0%, #fff 100%); }
.contact-card.telegram { border-color: #bae6fd; background: linear-gradient(180deg, #f0f9ff 0%, #fff 100%); }
.contact-card.wecom { border-color: #e2e8f0; }
.contact-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.contact-head strong { font-size: 15px; color: var(--ce-text); }
.contact-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  color: #fff;
  background: var(--ce-primary);
}
.contact-card.qq .contact-badge { background: #2563eb; }
.contact-card.wechat .contact-badge { background: #16a34a; }
.contact-card.telegram .contact-badge { background: #0284c7; }
.contact-account {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: #0f172a;
  margin-bottom: 6px;
}
.contact-tip {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--ce-muted);
}
.contact-qr {
  width: 168px;
  height: 168px;
  margin-bottom: 10px;
  padding: 8px;
  border: 1px solid var(--ce-border);
  border-radius: 12px;
  background: #fff;
}
.contact-actions { display: flex; flex-wrap: wrap; gap: 8px; }
@media (max-width: 640px) {
  .support-dock { right: 10px; bottom: 18px; top: auto; grid-template-columns: repeat(3, auto); transform: none; align-items: center; }
  .support-dock button { width: auto; min-height: 38px; padding: 0 14px; border-radius: 20px; writing-mode: initial; letter-spacing: 0; }
  .dock-icon { width: 40px !important; padding: 0 !important; }
  .form-grid { grid-template-columns: 1fr; gap: 0; }
}
</style>
