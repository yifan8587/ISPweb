<template>
  <div class="inquiries">
    <div class="bar">
      <el-radio-group v-model="statusFilter" @change="load">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="new">待处理</el-radio-button>
        <el-radio-button label="processing">跟进中</el-radio-button>
        <el-radio-button label="replied">已回复</el-radio-button>
        <el-radio-button label="closed">已关闭</el-radio-button>
      </el-radio-group>
      <span class="muted">客服回复会显示在此处</span>
    </div>

    <el-table :data="rows" v-loading="loading" stripe border>
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="detail">
            <div class="requirement"><b>提交需求：</b>{{ row.requirements || '-' }}</div>
            <el-divider content-position="left">客服回复</el-divider>
            <el-timeline v-if="row.replies?.length">
              <el-timeline-item
                v-for="reply in row.replies"
                :key="reply.id"
                :timestamp="formatDate(reply.created_at, true)"
                placement="top"
              >
                <div class="reply-author">{{ reply.operator_name }}</div>
                <div class="reply-content">{{ reply.content }}</div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="客服暂未回复，请耐心等待。" :image-size="56" />
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="inquiry_no" label="咨询编号" width="180" />
      <el-table-column prop="inquiry_type_label" label="类型" width="110" />
      <el-table-column prop="requirements" label="需求内容" min-width="280" show-overflow-tooltip />
      <el-table-column label="处理状态" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="statusTag(row.status)">{{ row.status_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="服务工单" width="180">
        <template #default="{ row }">{{ row.related_order_no || '-' }}</template>
      </el-table-column>
      <el-table-column label="最近回复" width="165">
        <template #default="{ row }">{{ formatDate(row.replied_at, true) || '-' }}</template>
      </el-table-column>
      <el-table-column label="提交时间" width="165">
        <template #default="{ row }">{{ formatDate(row.created_at, true) }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && !rows.length" description="暂未提交咨询需求" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getInquiries } from '@/api'
import { formatDate } from '@/utils/format'

const rows = ref([])
const loading = ref(false)
const statusFilter = ref('')

function statusTag(status) {
  return {
    new: 'info',
    processing: 'warning',
    replied: 'success',
    closed: 'info',
  }[status] || 'info'
}

async function load() {
  loading.value = true
  try {
    const params = { page_size: 100 }
    if (statusFilter.value) params.status = statusFilter.value
    const res = await getInquiries(params)
    rows.value = res.results || []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.bar { display:flex; align-items:center; justify-content:space-between; margin-bottom:18px; }
.detail { max-width:860px; padding:6px 22px 12px; }
.requirement, .reply-content { white-space:pre-wrap; line-height:1.65; }
.reply-author { font-weight:600; margin-bottom:5px; }
.muted { color:var(--ce-muted); font-size:13px; }
@media (max-width: 720px) { .bar { align-items:flex-start; flex-direction:column; gap:10px; } }
</style>
