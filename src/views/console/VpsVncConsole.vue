<template>
  <div class="vnc-page">
    <div class="vnc-toolbar">
      <div class="vnc-title">
        <el-button :icon="ArrowLeft" size="small" @click="goBack">返回</el-button>
        <span class="vnc-name">noVNC 控制台 — {{ vmName }}</span>
        <el-tag :type="stateTag.type" size="small" effect="plain">{{ stateTag.label }}</el-tag>
      </div>
      <div class="vnc-actions">
        <el-button size="small" @click="sendCtrlAltDel" :disabled="!connected">Ctrl+Alt+Del</el-button>
        <el-button size="small" @click="toggleFullscreen">全屏</el-button>
        <el-button size="small" type="primary" :loading="connecting" @click="connectVnc">重新连接</el-button>
      </div>
    </div>

    <div v-loading="connecting" class="vnc-wrap">
      <div ref="screenRef" class="vnc-screen" />
      <el-empty v-if="errorMsg && !connected" :description="errorMsg" class="vnc-error" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getMyVPSDetail, getVPSVncTicket, portalVncWebSocketURL } from '@/api'

const route = useRoute()
const router = useRouter()
const vpsId = ref(route.params.id)

const screenRef = ref(null)
const connecting = ref(false)
const connected = ref(false)
const errorMsg = ref('')
const vmName = ref('')
let rfb = null
let connectTimer = 0
let suppressDisconnect = false
let lastClose = null

const CLOSE_HINTS = {
  1006: '连接被网络或反向代理中断，请确认门户与管理端都放行了 WebSocket',
  4400: '这台虚机暂不能打开控制台',
  4401: '登录已失效，请重新登录',
  4403: '没有这台虚机的控制台权限',
  4404: '找不到这台虚机',
  4408: '控制台票据已失效，请重新连接',
  4500: '节点控制台配置不完整',
  4502: '管理端连不上节点或 PVE 控制台',
}

function closeMessage(close) {
  if (!close || close.code === 1000) return ''
  const hint = CLOSE_HINTS[close.code] || '连接被服务器关闭'
  const reason = close.reason ? `：${close.reason}` : ''
  return `${hint}（${close.code}${reason}）`
}

const stateTag = computed(() => {
  if (connected.value) return { type: 'success', label: '已连接' }
  if (connecting.value) return { type: 'warning', label: '连接中' }
  return { type: 'info', label: '未连接' }
})

function goBack() {
  if (window.opener) {
    window.close()
    return
  }
  router.push({ name: 'services' })
}

function clearConnectTimer() {
  if (!connectTimer) return
  clearTimeout(connectTimer)
  connectTimer = 0
}

function fail(message) {
  clearConnectTimer()
  connecting.value = false
  errorMsg.value = message
  ElMessage.error(message)
}

function apiMessage(error, fallback) {
  const data = error?.response?.data
  return data?.message || data?.detail || error?.message || fallback
}

async function loadVm() {
  try {
    const data = await getMyVPSDetail(vpsId.value)
    vmName.value = data?.name || data?.vps_no || `VPS ${vpsId.value}`
    if (data?.status && data.status !== 'running') {
      ElMessage.warning('虚机未处于运行状态，控制台可能无法连接')
    }
  } catch {
    vmName.value = `VPS ${vpsId.value}`
  }
}

async function connectVnc() {
  if (!screenRef.value) return
  errorMsg.value = ''
  connecting.value = true
  connected.value = false
  suppressDisconnect = true
  clearConnectTimer()

  if (rfb) {
    try { rfb.disconnect() } catch { /* ignore */ }
    rfb = null
  }
  suppressDisconnect = false
  while (screenRef.value.firstChild) screenRef.value.removeChild(screenRef.value.firstChild)

  // 提前加载 noVNC，避免拿到票据后再动态 import 的延迟（PVE 票据约 30 秒失效）
  let RFB
  try {
    const mod = await import('@novnc/novnc')
    RFB = mod.default || mod.RFB || mod
  } catch (e) {
    fail(e?.message || '无法加载 noVNC')
    return
  }

  // 先向 ISPmanager 取这台虚机的控制台票据，再连管理端的 VNC 中转。
  let wsUrl = ''
  let vncCred = null
  try {
    const resp = await getVPSVncTicket(vpsId.value)
    const payload = resp?.data && (resp.data.grant || resp.data.ticket || resp.data.password)
      ? resp.data
      : resp
    wsUrl = await portalVncWebSocketURL(vpsId.value, {
      grant: payload?.grant,
      ticket: payload?.ticket,
      port: payload?.port,
    })
    vncCred = payload?.password || payload?.ticket || null
  } catch (e) {
    connecting.value = false
    errorMsg.value = '获取 VNC 票据失败：' + apiMessage(e, '')
    return
  }
  if (!wsUrl) {
    fail(localStorage.getItem('ispweb_access') ? '节点未返回控制台票据' : '登录已失效，请重新登录')
    return
  }

  try {
    const opts = {}
    if (vncCred) opts.credentials = { password: vncCred }
    // 自己建 WebSocket 交给 noVNC：noVNC 的断开事件不带关闭码和原因，服务端给出的失败原因会丢失。
    lastClose = null
    const socket = new WebSocket(wsUrl, ['binary'])
    socket.addEventListener('close', (event) => {
      lastClose = { code: event.code, reason: event.reason }
    })
    rfb = new RFB(screenRef.value, socket, opts)
    rfb.scaleViewport = true
    rfb.resizeSession = false
    rfb.background = '#1a1a1a'
    connectTimer = window.setTimeout(() => {
      if (connected.value) return
      fail('控制台连接超时。请确认这台虚机正在运行，且管理端已用支持 WebSocket 的服务启动')
      disconnect()
    }, 45000)
    rfb.addEventListener('connect', () => {
      clearConnectTimer()
      connecting.value = false
      connected.value = true
      try { rfb.focus() } catch { /* ignore */ }
      ElMessage.success('VNC 已连接')
    })
    rfb.addEventListener('disconnect', (e) => {
      clearConnectTimer()
      connected.value = false
      connecting.value = false
      if (suppressDisconnect) return
      const detail = closeMessage(lastClose)
      if (e.detail?.clean && !detail) return
      errorMsg.value = detail ? `VNC 连接断开：${detail}` : 'VNC 连接断开'
      ElMessage.error(errorMsg.value)
    })
    rfb.addEventListener('credentialsrequired', () => {
      if (vncCred) {
        try { rfb.sendCredentials({ password: vncCred }) } catch { /* ignore */ }
      }
    })
    rfb.addEventListener('securityfailure', (e) => {
      fail(`VNC 鉴权失败：${e?.detail?.reason || '未知'}`)
    })
  } catch (e) {
    fail(e?.message || '建立 VNC 连接失败')
  }
}

function toggleFullscreen() {
  const el = screenRef.value
  if (!el) return
  if (!document.fullscreenElement) el.requestFullscreen?.()
  else document.exitFullscreen?.()
}

function sendCtrlAltDel() {
  if (rfb && rfb.sendCtrlAltDel) rfb.sendCtrlAltDel()
}

function disconnect() {
  clearConnectTimer()
  suppressDisconnect = true
  if (rfb) {
    try { rfb.disconnect() } catch { /* ignore */ }
    rfb = null
  }
}

onMounted(async () => {
  await loadVm()
  await connectVnc()
})
onUnmounted(disconnect)
</script>

<style scoped>
.vnc-page {
  box-sizing: border-box;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 16px;
  background: #f4f6fb;
}
.vnc-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.vnc-title { display: flex; align-items: center; gap: 10px; min-width: 0; }
.vnc-name { font-size: 16px; font-weight: 700; color: #1a1a2e; }
.vnc-actions { display: flex; flex-wrap: wrap; gap: 6px; }
.vnc-wrap {
  position: relative; flex: 1; min-height: 420px;
  background: #1a1a1a; border-radius: 8px; overflow: hidden;
}
.vnc-screen { width: 100%; height: 100%; min-height: 480px; }
.vnc-screen :deep(canvas) { margin: 0 auto; display: block; }
.vnc-error {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  width: min(420px, calc(100% - 24px));
}
@media (max-width: 640px) {
  .vnc-page { padding: 10px; }
  .vnc-wrap, .vnc-screen { min-height: 280px; }
}
</style>
