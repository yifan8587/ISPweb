import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'
import { getDashboard } from '@/api'

const SEEN_KEY = 'ispweb.seenReadyServices'

function readSeen() {
  try {
    const raw = JSON.parse(localStorage.getItem(SEEN_KEY) || '[]')
    return new Set(Array.isArray(raw) ? raw.map(String) : [])
  } catch {
    return new Set()
  }
}

function writeSeen(ids) {
  localStorage.setItem(SEEN_KEY, JSON.stringify([...ids].slice(-80)))
}

export function useProvisionNotices() {
  const router = useRouter()
  const provisioning = ref([])
  const ready = ref([])
  let timer = null

  async function refresh(notifyNew = true) {
    try {
      const res = await getDashboard()
      const data = res?.data || res || {}
      const notices = data.notices || { provisioning: [], ready: [] }
      provisioning.value = notices.provisioning || []
      ready.value = notices.ready || []
      if (!notifyNew) {
        const seen = readSeen()
        ready.value.forEach((item) => seen.add(String(item.id)))
        writeSeen(seen)
        return
      }
      const seen = readSeen()
      ready.value.forEach((item) => {
        const key = String(item.id)
        if (seen.has(key)) return
        seen.add(key)
        ElNotification({
          title: '服务已开通',
          message: `${item.product_name || item.instance_no || '新服务'} 已开通，可进入管理`,
          type: 'success',
          duration: 8000,
          onClick: () => router.push({ name: 'services' }),
        })
      })
      writeSeen(seen)
    } catch {
      // 轮询失败不打断控制台
    }
  }

  onMounted(() => {
    refresh(false)
    timer = window.setInterval(() => refresh(true), 20000)
  })

  onBeforeUnmount(() => {
    if (timer) window.clearInterval(timer)
  })

  return { provisioning, ready, refresh }
}
