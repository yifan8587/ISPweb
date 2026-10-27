<template>
  <div class="dashboard" v-loading="loading">
    <div class="welcome ce-card">
      <div>
        <h2>你好，{{ auth.displayName }} 👋</h2>
        <p class="muted">客户编号 {{ data.customer_no || '-' }} ·
          状态
          <el-tag size="small" :type="statusType">{{ statusText }}</el-tag>
        </p>
      </div>
      <el-button v-if="caps.order_create" type="primary" round @click="$router.push('/products')">
        <el-icon class="el-icon--left"><Plus /></el-icon> 选购新服务
      </el-button>
    </div>

    <div class="stat-grid">
      <div class="stat-card ce-card" v-for="s in statCards" :key="s.label">
        <div class="stat-ico" :style="{ background: s.bg, color: s.color }">
          <el-icon :size="22"><component :is="s.icon" /></el-icon>
        </div>
        <div>
          <div class="stat-num">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <div class="cols">
      <div class="ce-card panel">
        <div class="panel-head">
          <h3>账务概览</h3>
          <router-link to="/console/bills" class="more">账单中心 →</router-link>
        </div>
        <div class="finance">
          <div class="fin-item">
            <span>账户余额</span>
            <b>{{ money(data.balance) }}</b>
            <router-link v-if="caps.billing_pay" to="/console/bills?recharge=1" class="more">充值</router-link>
          </div>
          <div class="fin-item">
            <span>信用额度</span>
            <b>{{ money(data.credit_limit) }}</b>
          </div>
          <div class="fin-item" v-if="data.reputation_visible">
            <span>信誉值余额</span>
            <b>{{ data.reputation_balance }} / {{ data.reputation_quota }}</b>
          </div>
          <div class="fin-item">
            <span>预计月支出</span>
            <b>{{ money(data.monthly_cost) }}</b>
          </div>
          <div class="fin-item danger" v-if="data.outstanding_amount">
            <span>待支付金额</span>
            <b>{{ money(data.outstanding_amount) }}</b>
          </div>
        </div>
      </div>

      <div class="ce-card panel">
        <div class="panel-head">
          <h3>快捷入口</h3>
        </div>
        <div class="quick">
          <router-link to="/console/services" class="quick-item">
            <el-icon><Connection /></el-icon><span>我的服务</span>
          </router-link>
          <router-link to="/console/resources" class="quick-item">
            <el-icon><Cpu /></el-icon><span>资源管理</span>
          </router-link>
          <router-link to="/console/orders" class="quick-item">
            <el-icon><Document /></el-icon><span>我的订单</span>
          </router-link>
          <router-link to="/console/profile" class="quick-item">
            <el-icon><User /></el-icon><span>账户资料</span>
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getDashboard } from '@/api'
import { useAuthStore } from '@/store/auth'
import { useCapabilities } from '@/composables/useCapabilities'
import { money } from '@/utils/format'

const auth = useAuthStore()
const { caps } = useCapabilities()
const loading = ref(false)
const data = ref({})

const statusMap = {
  active: { text: '正常', type: 'success' },
  pending: { text: '待激活', type: 'warning' },
  suspended: { text: '已暂停', type: 'danger' },
  closed: { text: '已关闭', type: 'info' },
}
const statusText = computed(() => statusMap[data.value.status]?.text || data.value.status || '-')
const statusType = computed(() => statusMap[data.value.status]?.type || 'info')

const statCards = computed(() => [
  { label: '运行中服务', value: data.value.active_services ?? 0, icon: 'Connection', bg: '#eff6ff', color: '#2563eb' },
  { label: 'VPS 主机', value: data.value.vps_count ?? 0, icon: 'Cpu', bg: '#ecfeff', color: '#0891b2' },
  { label: '公网对接', value: data.value.edge_count ?? 0, icon: 'Promotion', bg: '#f5f3ff', color: '#7c3aed' },
  { label: '处理中订单', value: data.value.pending_orders ?? 0, icon: 'Document', bg: '#fffbeb', color: '#d97706' },
])

onMounted(async () => {
  loading.value = true
  try {
    const res = await getDashboard()
    data.value = res.data || res
    auth.setCapabilities(data.value.capabilities)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.welcome {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 26px;
  margin-bottom: 20px;
}
.welcome h2 {
  margin: 0 0 6px;
  font-size: 22px;
}
.welcome p {
  margin: 0;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
  margin-bottom: 20px;
}
.stat-card {
  padding: 22px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.stat-ico {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stat-num {
  font-size: 28px;
  font-weight: 800;
}
.stat-label {
  color: var(--ce-muted);
  font-size: 14px;
}
.cols {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 18px;
}
.panel {
  padding: 22px 24px;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}
.panel-head h3 {
  margin: 0;
  font-size: 17px;
}
.more {
  color: var(--ce-primary);
  font-size: 14px;
}
.finance {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.fin-item {
  background: var(--ce-bg);
  border-radius: 12px;
  padding: 16px 18px;
}
.fin-item span {
  display: block;
  color: var(--ce-muted);
  font-size: 13px;
  margin-bottom: 6px;
}
.fin-item b {
  font-size: 22px;
}
.fin-item.danger b {
  color: #ef4444;
}
.quick {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.quick-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  background: var(--ce-bg);
  border-radius: 12px;
  color: #374151;
  font-weight: 600;
  transition: all 0.2s;
}
.quick-item:hover {
  background: #eef2ff;
  color: var(--ce-primary);
  transform: translateY(-2px);
}
.quick-item .el-icon {
  font-size: 24px;
}
@media (max-width: 980px) {
  .stat-grid {
    grid-template-columns: 1fr 1fr;
  }
  .cols {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 640px) {
  .stat-grid,
  .finance,
  .quick {
    grid-template-columns: 1fr;
  }
  .panel { padding: 16px; }
}
</style>
