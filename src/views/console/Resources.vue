<template>
  <div class="resources">
    <el-tabs v-model="tab">
      <el-tab-pane label="VPS 主机" name="vps">
        <el-table :data="vpsRows" v-loading="loadingVps" stripe border>
          <el-table-column prop="vps_no" label="VPS ID" width="160" />
          <el-table-column prop="name" label="名称" min-width="130" />
          <el-table-column label="配置" min-width="170">
            <template #default="{ row }">
              {{ row.vcpu }}核 / {{ ramText(row.ram_mb) }} / {{ row.disk_gb }}G / {{ row.bandwidth_mbps }}M
            </template>
          </el-table-column>
          <el-table-column label="系统" width="130">
            <template #default="{ row }">{{ row.os_label || row.os_version || '-' }}</template>
          </el-table-column>
          <el-table-column label="管理 IP" width="140">
            <template #default="{ row }">
              <span class="mono">{{ row.mgmt_ip || '-' }}</span>
              <span v-if="row.mgmt_ip" class="muted sm"> :{{ row.mgmt_port }}</span>
            </template>
          </el-table-column>
          <el-table-column label="节点" width="150">
            <template #default="{ row }">
              {{ row.pop_name }}
              <div class="muted sm">{{ [row.country_name, row.city_name].filter(Boolean).join('·') }}</div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="vpsStatusTag[row.status]?.type || 'info'">
                {{ vpsStatusTag[row.status]?.label || row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="到期" width="120">
            <template #default="{ row }">{{ formatDate(row.expire_time) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openManage(row, 'vps')">管理</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loadingVps && !vpsRows.length" description="暂无 VPS 主机" />
      </el-tab-pane>

      <el-tab-pane label="公网对接" name="edge">
        <el-table :data="edgeRows" v-loading="loadingEdge" stripe border>
          <el-table-column prop="edge_no" label="加速编号" width="170" />
          <el-table-column prop="name" label="名称" min-width="130" />
          <el-table-column prop="protocol_label" label="协议" width="120" />
          <el-table-column label="带宽" width="110">
            <template #default="{ row }">{{ row.bandwidth_mbps }} Mbps</template>
          </el-table-column>
          <el-table-column label="节点" width="160">
            <template #default="{ row }">
              {{ row.pop_name }}
              <div class="muted sm">{{ [row.country_name, row.city_name].filter(Boolean).join('·') }}</div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">{{ row.status_label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="到期" width="120">
            <template #default="{ row }">{{ formatDate(row.expire_time) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openManage(row, 'edge')">管理</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loadingEdge && !edgeRows.length" description="暂无公网对接服务" />
      </el-tab-pane>
    </el-tabs>

    <ServiceManageDrawer v-model="manageVisible" :service="current" @refresh="reloadCurrent" />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { getMyEdge, getMyVPS } from '@/api'
import ServiceManageDrawer from './ServiceManageDrawer.vue'
import { formatDate, ramText, vpsStatusTag } from '@/utils/format'

const tab = ref('vps')
const vpsRows = ref([])
const edgeRows = ref([])
const loadingVps = ref(false)
const loadingEdge = ref(false)
const manageVisible = ref(false)
const current = ref(null)
let edgeLoaded = false

function openManage(row, serviceType) {
  current.value = {
    service_type: serviceType,
    service_type_label: serviceType === 'vps' ? 'VPS' : '公网对接',
    instance_no: row.vps_no || row.edge_no,
    resource: { id: row.id },
  }
  manageVisible.value = true
}

function reloadCurrent() {
  if (current.value?.service_type === 'edge') return loadEdge()
  return loadVps()
}

async function loadVps() {
  loadingVps.value = true
  try {
    const res = await getMyVPS({ page_size: 100 })
    vpsRows.value = res.results || []
  } finally {
    loadingVps.value = false
  }
}
async function loadEdge() {
  loadingEdge.value = true
  try {
    const res = await getMyEdge({ page_size: 100 })
    edgeRows.value = res.results || []
    edgeLoaded = true
  } finally {
    loadingEdge.value = false
  }
}

watch(tab, (t) => {
  if (t === 'edge' && !edgeLoaded) loadEdge()
})

onMounted(loadVps)
</script>

<style scoped>
.mono {
  font-family: 'SFMono-Regular', Consolas, monospace;
}
.sm {
  font-size: 12px;
}
</style>
