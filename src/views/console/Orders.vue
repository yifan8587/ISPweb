<template>
  <div class="orders">
    <div class="bar">
      <el-radio-group v-model="statusFilter" @change="load">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="pending">待审批</el-radio-button>
        <el-radio-button label="provisioning">开通中</el-radio-button>
        <el-radio-button label="active">服务中</el-radio-button>
        <el-radio-button label="rejected">已驳回</el-radio-button>
      </el-radio-group>
      <el-button v-if="caps.order_create" type="primary" round @click="$router.push('/products')">
        <el-icon class="el-icon--left"><Plus /></el-icon> 新建订单
      </el-button>
    </div>

    <el-table :data="rows" v-loading="loading" stripe border>
      <el-table-column prop="order_no" label="工单编号" width="170" />
      <el-table-column label="类型" width="110">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.order_type_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="business_type_label" label="业务" width="130" />
      <el-table-column label="节点 / 需求" min-width="200">
        <template #default="{ row }">
          <div>{{ row.pop_name || '-' }}</div>
          <div class="muted sm">{{ reqText(row) }} ×{{ row.requested_quantity || 1 }}</div>
        </template>
      </el-table-column>
      <el-table-column label="交付进度" width="130">
        <template #default="{ row }">
          <el-tag size="small" :type="deliveryStatusTag(customerDeliveryStatus(row))">
            {{ deliveryStatusLabel(customerDeliveryStatus(row)) }}
          </el-tag>
          <div class="muted sm">{{ row.delivery_summary?.active_count || 0 }}/{{ row.delivery_summary?.expected_quantity || row.requested_quantity || 1 }} 已启用</div>
        </template>
      </el-table-column>
      <el-table-column label="报价" width="130">
        <template #default="{ row }">{{ row.quoted_price ? money(row.quoted_price, row.fx_quote_currency || 'USD') : '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="orderStatusTag[row.status]?.type || 'info'">
            {{ orderStatusTag[row.status]?.label || row.status }}
          </el-tag>
          <el-tooltip
            v-if="row.auto_provision_message"
            :content="row.auto_provision_message"
            placement="top"
          >
            <div class="muted sm provision-state">{{ row.auto_provision_status_label }}</div>
          </el-tooltip>
          <div v-if="row.manual_delivery?.open" class="muted sm">
            {{ row.manual_delivery.reason_label }} {{ row.manual_delivery.done_count }}/{{ row.manual_delivery.total_count }}
          </div>
        </template>
      </el-table-column>
      <el-table-column label="提交时间" width="160">
        <template #default="{ row }">{{ formatDate(row.created_at, true) }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && !rows.length" description="暂无订单" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getOrders } from '@/api'
import { useCapabilities } from '@/composables/useCapabilities'
import { formatDate, money, orderStatusTag, ramText } from '@/utils/format'

const { caps } = useCapabilities()
const rows = ref([])
const loading = ref(false)
const statusFilter = ref('')

function reqText(row) {
  const parts = []
  const isEdge = String(row.business_type || '').startsWith('edge')
  if (!isEdge) {
    if (row.requested_vcpu) parts.push(`${row.requested_vcpu}核`)
    if (row.requested_ram_mb) parts.push(ramText(row.requested_ram_mb))
    if (row.requested_disk_gb) parts.push(`${row.requested_disk_gb}G`)
  }
  if (row.requested_bandwidth_mbps) parts.push(`${row.requested_bandwidth_mbps}M`)
  if (row.requested_ip_count) parts.push(`${row.requested_ip_count}IP`)
  if (row.requested_os) parts.push(row.requested_os)
  return parts.join(' / ') || row.requirements || '-'
}
function customerDeliveryStatus(row) {
  if (row.delivery_summary?.status === 'delivered' || row.auto_provision_status === 'success') return 'delivered'
  if (
    row.auto_provision_status === 'insufficient'
    || row.manual_delivery?.reason === 'stock'
    || row.is_backorder && row.manual_delivery?.open
  ) return 'waiting_admin'
  return row.delivery_summary?.status
}
function deliveryStatusLabel(status) {
  return {
    not_started: '待交付',
    waiting_admin: '待管理员交付',
    partial: '部分交付',
    delivered: '已交付',
    pending: '处理中',
    terminated: '已终止',
  }[status] || '待交付'
}
function deliveryStatusTag(status) {
  return {
    not_started: 'info',
    waiting_admin: 'warning',
    partial: 'warning',
    delivered: 'success',
    pending: 'primary',
    terminated: 'info',
  }[status] || 'info'
}

async function load() {
  loading.value = true
  try {
    const params = { page_size: 100 }
    if (statusFilter.value) params.status = statusFilter.value
    const res = await getOrders(params)
    rows.value = res.results || []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 18px;
}
.sm {
  font-size: 12px;
}
.provision-state {
  overflow: hidden;
  margin-top: 4px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
