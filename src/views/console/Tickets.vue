<template>
  <div class="tickets">
    <div class="bar">
      <el-radio-group v-model="statusFilter" @change="load">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="open">待处理</el-radio-button>
        <el-radio-button label="in_progress">处理中</el-radio-button>
        <el-radio-button label="pending_customer">待我回复</el-radio-button>
        <el-radio-button label="resolved">已解决</el-radio-button>
        <el-radio-button label="closed">已关闭</el-radio-button>
      </el-radio-group>
      <el-button v-if="caps.ticket_manage" type="primary" @click="createVisible = true">提交工单</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" stripe border>
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="detail">
            <div class="requirement"><b>问题描述：</b>{{ row.description || '-' }}</div>
            <el-divider content-position="left">往来记录</el-divider>
            <el-timeline v-if="row.messages?.length">
              <el-timeline-item
                v-for="msg in row.messages"
                :key="msg.id"
                :timestamp="formatDate(msg.created_at, true)"
                placement="top"
              >
                <div class="reply-author">{{ msg.author_name }}</div>
                <div class="reply-content">{{ msg.content }}</div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无往来记录" :image-size="56" />
            <div v-if="caps.ticket_manage && row.status !== 'closed'" class="reply-box">
              <el-input v-model="replyDraft[row.id]" type="textarea" :rows="3" placeholder="补充说明或回复客服" />
              <el-button type="primary" :loading="replyingId === row.id" @click="sendReply(row)">发送回复</el-button>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="ticket_no" label="工单编号" width="180" />
      <el-table-column prop="subject" label="主题" min-width="220" show-overflow-tooltip />
      <el-table-column prop="category_label" label="分类" width="110" />
      <el-table-column prop="priority_label" label="优先级" width="110" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag size="small" :type="statusTag(row.status)">{{ row.status_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="提交时间" width="165">
        <template #default="{ row }">{{ formatDate(row.created_at, true) }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && !rows.length" description="暂无技术工单" />

    <el-dialog v-model="createVisible" title="提交技术工单" width="520px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="分类">
          <el-select v-model="createForm.category" style="width:100%">
            <el-option label="技术故障" value="technical" />
            <el-option label="滥用投诉" value="abuse" />
            <el-option label="财务" value="billing" />
            <el-option label="接入" value="access" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="createForm.priority" style="width:100%">
            <el-option label="P1 紧急" value="p1" />
            <el-option label="P2 高" value="p2" />
            <el-option label="P3 普通" value="p3" />
            <el-option label="P4 低" value="p4" />
          </el-select>
        </el-form-item>
        <el-form-item label="主题" required>
          <el-input v-model="createForm.subject" maxlength="200" />
        </el-form-item>
        <el-form-item label="问题描述" required>
          <el-input v-model="createForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createTicket, getTickets, replyTicket } from '@/api'
import { useCapabilities } from '@/composables/useCapabilities'
import { formatDate } from '@/utils/format'

const { caps } = useCapabilities()
const rows = ref([])
const loading = ref(false)
const statusFilter = ref('')
const createVisible = ref(false)
const creating = ref(false)
const replyingId = ref(null)
const replyDraft = reactive({})
const createForm = reactive({
  category: 'technical',
  priority: 'p3',
  subject: '',
  description: '',
})

function statusTag(status) {
  return {
    open: 'danger',
    in_progress: 'warning',
    pending_customer: 'info',
    waiting: 'info',
    resolved: 'success',
    closed: 'info',
  }[status] || 'info'
}

async function load() {
  loading.value = true
  try {
    const params = { page_size: 100 }
    if (statusFilter.value) params.status = statusFilter.value
    const res = await getTickets(params)
    rows.value = res.results || []
  } finally {
    loading.value = false
  }
}

async function submitCreate() {
  if (!createForm.subject.trim() || !createForm.description.trim()) {
    return ElMessage.warning('请填写主题和描述')
  }
  creating.value = true
  try {
    await createTicket({ ...createForm })
    ElMessage.success('工单已提交')
    createVisible.value = false
    Object.assign(createForm, { category: 'technical', priority: 'p3', subject: '', description: '' })
    await load()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '提交失败')
  } finally {
    creating.value = false
  }
}

async function sendReply(row) {
  const content = (replyDraft[row.id] || '').trim()
  if (!content) return ElMessage.warning('请填写回复内容')
  replyingId.value = row.id
  try {
    await replyTicket(row.id, { content })
    replyDraft[row.id] = ''
    ElMessage.success('回复已发送')
    await load()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '回复失败')
  } finally {
    replyingId.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.bar { display:flex; align-items:center; justify-content:space-between; margin-bottom:18px; gap:12px; }
.detail { max-width:860px; padding:6px 22px 12px; }
.requirement, .reply-content { white-space:pre-wrap; line-height:1.65; }
.reply-author { font-weight:600; margin-bottom:5px; }
.reply-box { display:flex; flex-direction:column; align-items:flex-start; gap:10px; margin-top:16px; }
.reply-box .el-input { width:100%; }
@media (max-width: 720px) { .bar { align-items:flex-start; flex-direction:column; } }
</style>
