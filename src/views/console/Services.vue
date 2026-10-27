<template>
  <div class="services">
    <el-alert
      v-if="paidJustNow"
      class="paid-alert"
      type="success"
      :closable="true"
      show-icon
      title="支付已完成。库存充足时会自动开通；库存不足时请到「我的订单」查看「待管理员交付」，交付完成后服务会出现在本页。"
      @close="clearPaidQuery"
    />
    <div class="bar">
      <el-radio-group v-model="statusFilter" @change="load">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="active">运行中</el-radio-button>
        <el-radio-button label="provisioning">开通中</el-radio-button>
        <el-radio-button label="suspended">已暂停</el-radio-button>
        <el-radio-button label="terminated">已终止</el-radio-button>
      </el-radio-group>
      <el-button v-if="caps.order_create" type="primary" round @click="$router.push('/products')">
        <el-icon class="el-icon--left"><Plus /></el-icon> 选购新服务
      </el-button>
    </div>

    <el-table
      class="services-table"
      :data="rows"
      v-loading="loading"
      stripe
      border
      native-scrollbar
      :scrollbar-tabindex="0"
      aria-label="服务列表，可横向滚动查看全部列"
    >
      <el-table-column prop="instance_no" label="实例编号" width="170" />
      <el-table-column label="类型" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="row.service_type === 'vps' ? 'primary' : 'success'">
            {{ row.service_type === 'edge' ? '公网对接' : (row.service_type_label || 'VPS') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="节点 / 产品" min-width="180">
        <template #default="{ row }">
          <div>{{ row.pop_name || '-' }}</div>
          <div class="muted sm">{{ row.product_name || '未关联产品' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="规格" min-width="180">
        <template #default="{ row }">{{ specText(row) }}</template>
      </el-table-column>
      <el-table-column label="月费" width="130">
        <template #default="{ row }">
          <b>{{ money(row.monthly_fee_effective, row.fee_currency) }}</b>
          <el-tag v-if="row.is_trial" size="small" type="warning" effect="plain" style="margin-left:4px">测试</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag
            size="small"
            :type="row.needs_protocol_config ? 'warning' : (instanceStatusTag[row.status]?.type || 'info')"
          >
            {{ row.needs_protocol_config ? '待配置' : (row.status_label || instanceStatusTag[row.status]?.label || row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="到期时间" width="120">
        <template #default="{ row }">{{ formatDate(row.expire_time) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" :disabled="!row.resource"
                     @click="openManage(row)">管理</el-button>
          <el-tag v-if="row.needs_protocol_config" size="small" type="warning" class="ml-tag">待补全</el-tag>
          <el-tooltip
            :disabled="!(!canChangeService || row.status === 'terminated' || !row.can_change_request)"
            :content="changeDisabledReason(row)"
            placement="top"
          >
            <el-button link type="primary" size="small"
                       :disabled="!canChangeService || row.status === 'terminated' || !row.can_change_request"
                       @click="openChange(row)">变更</el-button>
            <el-button v-if="row.is_trial" link type="warning" size="small"
                       :disabled="!canChangeService || row.status === 'terminated' || !row.can_change_request"
                       @click="openPay(row)">转正式</el-button>
          </el-tooltip>
        </template>
      </el-table-column>
    </el-table>

    <el-alert
      v-if="dueReminders.length"
      class="mb"
      type="warning"
      show-icon
      :closable="false"
      title="有服务即将到期。正式服务请在到期前完成续费支付；测试服务请转为正式使用并支付。未支付的，到期次日收回 VPS、隧道、IP 和带宽。"
    >
      <el-button
        v-for="row in dueReminders"
        :key="row.id"
        link
        type="primary"
        @click="openPay(row)"
      >
        {{ row.instance_no }} · {{ row.is_trial ? '转为正式' : '去续费' }}
      </el-button>
    </el-alert>

    <el-empty v-if="!loading && !rows.length" description="暂无服务，去选购一个吧" />

    <ServiceManageDrawer v-model="manageVisible" :service="current" @refresh="load" />

    <el-dialog
      v-model="changeVisible"
      title="服务变更"
      width="760px"
      destroy-on-close
      @closed="resetChangeDialog"
    >
      <el-form v-if="changePhase === 'form'" label-position="top">
        <el-form-item label="变更类型">
          <el-radio-group v-model="changeForm.change_type">
            <el-radio-button value="spec">调整规格</el-radio-button>
            <el-radio-button v-if="current?.service_type === 'edge'" value="replace_ip">申请替换 IP</el-radio-button>
            <el-radio-button value="renew">续期</el-radio-button>
            <el-radio-button v-if="current?.is_trial" value="convert">转为正式</el-radio-button>
            <el-radio-button value="terminate">申请终止</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="changeForm.change_type === 'renew' || changeForm.change_type === 'convert'">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            class="mb"
            :title="changeForm.change_type === 'convert'
              ? '按当前规格选择账期支付。支付完成后写入正式开通日和到期日，服务转为正式使用。'
              : '按当前规格选择账期直接出账支付，支付成功后自动延长到期日，不必再等人工审批续期工单。'"
          />
          <el-form-item label="续费账期">
            <el-radio-group v-model="changeForm.billing_cycle">
              <el-radio-button value="monthly">1 个月</el-radio-button>
              <el-radio-button value="quarterly">3 个月</el-radio-button>
              <el-radio-button value="semi_annual">半年</el-radio-button>
              <el-radio-button value="annual">1 年</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <div v-loading="quoting" class="quote-box">
            <div class="quote-title">{{ changeForm.change_type === 'convert' ? '转正式报价' : '续费报价' }}</div>
            <div v-if="quote" class="quote-grid">
              <div class="quote-item">
                <span>当前月费</span>
                <strong>{{ money(quote.monthly_fee, quote.currency) }}</strong>
              </div>
              <div class="quote-item">
                <span>账期</span>
                <strong>{{ quote.billing_cycle_label }} × {{ quote.months }} 个月</strong>
              </div>
              <div class="quote-item">
                <span>当前到期</span>
                <strong>{{ quote.current_expire || '未设置（从今天起算）' }}</strong>
              </div>
              <div class="quote-item">
                <span>{{ changeForm.change_type === 'convert' ? '正式到期' : '续费后到期' }}</span>
                <strong class="accent">{{ quote.new_expire }}</strong>
              </div>
              <div class="quote-item">
                <span>本次应付</span>
                <strong>{{ money(quote.due_now, quote.currency) }}</strong>
              </div>
            </div>
            <el-alert
              v-if="quote"
              class="mt"
              type="warning"
              :closable="false"
              show-icon
              :title="quote.policy_text"
            />
            <el-empty v-else-if="!quoting" description="选择账期后将自动估算续费金额" :image-size="48" />
          </div>
          <el-form-item
            v-if="needsPayment"
            label="在线支付渠道"
            required
          >
            <div v-loading="paymentMethodsLoading" class="payment-methods">
              <el-radio-group v-model="selectedPaymentChannel" class="payment-radio-group">
                <el-radio
                  v-for="method in onlinePaymentMethods"
                  :key="method.channel_id"
                  :label="method.channel_id"
                  border
                  class="payment-radio"
                >
                  {{ method.label || method.provider_label }}
                </el-radio>
              </el-radio-group>
              <el-alert
                v-if="!paymentMethodsLoading && !onlinePaymentMethods.length"
                type="warning"
                :closable="false"
                show-icon
                title="暂无可用在线支付渠道，提交后可在账单页继续支付。"
              />
            </div>
          </el-form-item>
        </template>

        <template v-if="changeForm.change_type === 'replace_ip'">
          <el-alert
            type="warning"
            :closable="false"
            show-icon
            class="mb"
            title="替换 IP 不会自动释放或重分配地址，提交后进入人工确认。运维核对原地址与新地址后再下发。"
          />
          <div v-loading="quoting" class="quote-box">
            <el-alert
              v-if="quote"
              :type="quoteAlertType"
              :closable="false"
              show-icon
              :title="quote.policy_text"
            />
          </div>
        </template>

        <template v-if="changeForm.change_type === 'spec'">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            class="mb"
            title="协议或接口参数请到「管理」页配置。这里处理 CPU / 内存 / 硬盘、带宽增减与指定 IP 释放 / 新增。确认后由 ISPmanager 下发到对应 POP 的 PVE：增加按剩余天数折算加收，减少折算减费并立即生效。"
          />

          <div class="origin-box">
            <div class="quote-title">原服务</div>
            <div class="origin-grid">
              <div><span>实例</span><strong>{{ current?.instance_no || '—' }}</strong></div>
              <div><span>节点 / 产品</span><strong>{{ current?.pop_name || '—' }} / {{ current?.product_name || '—' }}</strong></div>
              <div><span>原带宽</span><strong>{{ originalBandwidth }} Mbps</strong></div>
              <div><span>原月费</span><strong>{{ money(current?.monthly_fee_effective, current?.fee_currency) }}</strong></div>
              <div><span>原分配 IP</span><strong>{{ currentAllocatedCount }} 个</strong></div>
            </div>
          </div>

          <template v-if="current?.service_type === 'vps'">
            <div class="row3">
              <el-form-item label="vCPU">
                <el-input-number v-model="changeForm.requested_vcpu" :min="1" controls-position="right" style="width:100%" />
              </el-form-item>
              <el-form-item label="内存 (GB)">
                <el-input-number v-model="requestedRamGb" :min="1" :step="1" controls-position="right" style="width:100%" />
              </el-form-item>
              <el-form-item label="硬盘 (GB)">
                <el-input-number v-model="changeForm.requested_disk_gb" :min="1" controls-position="right" style="width:100%" />
              </el-form-item>
            </div>
          </template>

          <el-form-item label="带宽变更">
            <el-radio-group v-model="bwMode">
              <el-radio-button value="keep">不调整</el-radio-button>
              <el-radio-button value="increase">新增带宽</el-radio-button>
              <el-radio-button value="decrease">减少带宽</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <div class="row2">
            <el-form-item v-if="bwMode !== 'keep'" :label="bwMode === 'increase' ? '新增带宽 (Mbps)' : '减少带宽 (Mbps)'">
              <el-input-number v-model="bwDelta" :min="1" controls-position="right" style="width:100%" />
            </el-form-item>
            <el-form-item label="变更后带宽">
              <div class="target-bw">{{ targetBandwidth }} Mbps</div>
            </el-form-item>
          </div>

          <div class="ip-box" v-loading="quoting && !allocatedIps.length">
            <div class="quote-title">原分配 IP</div>
            <el-table v-if="allocatedIps.length" :data="allocatedIps" size="small" border>
              <el-table-column label="IP 地址" min-width="150">
                <template #default="{ row }">
                  <span :class="{ released: isIpReleased(row.id) }" class="mono">
                    {{ row.address }}<template v-if="row.prefix_len != null">/{{ row.prefix_len }}</template>
                  </span>
                  <el-tag v-if="row.is_primary" size="small" type="success" class="ml-tag">主</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="路由" min-width="130">
                <template #default="{ row }">
                  <span class="mono">{{ row.route_cidr || `${row.address}/32` }}</span>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag size="small" :type="isIpReleased(row.id) ? 'info' : (row.route_status === 'pushed' ? 'success' : 'warning')">
                    {{ isIpReleased(row.id) ? '将释放' : (row.route_status_label || '已分配') }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100" align="right">
                <template #default="{ row }">
                  <el-button
                    v-if="!isIpReleased(row.id)"
                    link
                    type="danger"
                    size="small"
                    @click="markReleaseIp(row)"
                  >释放</el-button>
                  <el-button v-else link type="primary" size="small" @click="undoReleaseIp(row)">撤销</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else-if="!quoting" description="当前没有已分配的业务 IP" :image-size="48" />
            <div class="row2" style="margin-top:12px">
              <el-form-item label="新增 IP 数量">
                <el-input-number v-model="addIpCount" :min="0" controls-position="right" style="width:100%" />
              </el-form-item>
              <el-form-item label="变更后 IP 数量">
                <div class="target-bw">{{ targetIpCount }}</div>
              </el-form-item>
            </div>
          </div>

          <div v-loading="quoting" class="quote-box">
            <div class="quote-title">费用对比</div>
            <div v-if="quote" class="quote-grid">
              <div class="quote-item">
                <span>原服务月费</span>
                <strong>{{ money(quote.old_monthly_fee, quote.currency) }}</strong>
              </div>
              <div class="quote-item">
                <span>变更后月费</span>
                <strong class="accent">{{ money(quote.new_monthly_fee, quote.currency) }}</strong>
              </div>
              <div class="quote-item">
                <span>月费差额</span>
                <strong :class="deltaClass">{{ money(quote.monthly_delta, quote.currency) }}</strong>
              </div>
              <div class="quote-item">
                <span>{{ Number(quote.credit_now) > 0 ? '本期减少' : '本次应付' }}</span>
                <strong>{{ money(Number(quote.credit_now) > 0 ? quote.credit_now : quote.due_now, quote.currency) }}</strong>
              </div>
            </div>
            <el-alert
              v-if="quote"
              class="mt"
              :type="quoteAlertType"
              :closable="false"
              show-icon
              :title="quote.policy_text"
            />
            <div v-if="quote" class="quote-meta">
              生效时间：{{ quote.effective_at || '—' }}
              <template v-if="quote.direction === 'upgrade' || quote.direction === 'downgrade'">
                · 本月剩余 {{ quote.remaining_days }} / {{ quote.days_in_month }} 天折算
              </template>
            </div>
            <el-empty v-else-if="!quoting" description="调整规格后将自动估算费用" :image-size="48" />
          </div>

          <el-form-item
            v-if="needsPayment"
            label="在线支付渠道"
            required
          >
            <div v-loading="paymentMethodsLoading" class="payment-methods">
              <el-radio-group v-model="selectedPaymentChannel" class="payment-radio-group">
                <el-radio
                  v-for="method in onlinePaymentMethods"
                  :key="method.channel_id"
                  :label="method.channel_id"
                  border
                  class="payment-radio"
                >
                  {{ method.label || method.provider_label }}
                </el-radio>
              </el-radio-group>
              <el-alert
                v-if="!paymentMethodsLoading && !onlinePaymentMethods.length"
                type="warning"
                :closable="false"
                show-icon
                title="暂无可用在线支付渠道，提交后可在账单页继续支付。"
              />
            </div>
          </el-form-item>
        </template>

        <el-form-item label="补充说明">
          <el-input v-model="changeForm.requirements" type="textarea" :rows="3" placeholder="请描述您的变更需求（可选）" />
        </el-form-item>
      </el-form>

      <div v-else class="change-result">
        <el-alert
          :type="changeSteps.some((s) => s.status === 'error') ? 'warning' : 'success'"
          :closable="false"
          show-icon
          class="mb"
          :title="changeResultMessage || '变更成功'"
        />
        <div class="push-steps">
          <div v-for="step in changeSteps" :key="step.key" class="push-step" :class="step.status">
            <el-icon v-if="step.status === 'done'"><CircleCheckFilled /></el-icon>
            <el-icon v-else-if="step.status === 'error'"><CircleCloseFilled /></el-icon>
            <el-icon v-else-if="step.status === 'warn'"><WarnTriangleFilled /></el-icon>
            <el-icon v-else><Clock /></el-icon>
            <div>
              <div class="push-label">{{ step.label }}</div>
              <div v-if="step.detail" class="push-detail">{{ step.detail }}</div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="changeVisible = false">{{ changePhase === 'result' ? '关闭' : '取消' }}</el-button>
        <el-button
          v-if="changePhase === 'form'"
          type="primary"
          :loading="submitting"
          @click="submitChange"
        >
          {{ submitButtonText }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="qrPayVisible"
      :title="checkoutTitle"
      width="380px"
      :close-on-click-modal="false"
      @closed="stopPaymentPolling"
    >
      <div class="qr-payment">
        <img v-if="qrCodeImage" :src="qrCodeImage" alt="支付二维码">
        <el-skeleton v-else :rows="4" animated />
        <p>{{ activePayment?.currency }}{{ activePayment?.amount }}</p>
        <p class="qr-status">
          {{ checkoutHint }}
        </p>
      </div>
      <template #footer>
        <el-button @click="router.push({ name: 'bills' })">前往账单查看</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import QRCode from 'qrcode'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getBillPaymentMethods,
  getOrder,
  getPaymentTransaction,
  getServices,
  quoteServiceChange,
  quoteServiceRenew,
  quoteTrialConvert,
  renewService,
  convertTrialService,
  requestServiceChange,
} from '@/api'
import ServiceManageDrawer from './ServiceManageDrawer.vue'
import { useAuthStore } from '@/store/auth'
import { useCapabilities } from '@/composables/useCapabilities'
import { launchCheckout } from '@/utils/checkout'
import { formatDate, gbToMb, instanceStatusTag, mbToGb, money, ramText } from '@/utils/format'

const auth = useAuthStore()
const { caps } = useCapabilities()
const canChangeService = computed(() => caps.value.service_change)

const router = useRouter()
const route = useRoute()
const paidJustNow = computed(() => route.query.paid === '1')

function clearPaidQuery() {
  const query = { ...route.query }
  delete query.paid
  router.replace({ name: 'services', query })
}
const rows = ref([])
const loading = ref(false)
const statusFilter = ref('')
const manageVisible = ref(false)
const changeVisible = ref(false)
const submitting = ref(false)
const quoting = ref(false)
const current = ref(null)
const quote = ref(null)
const paymentMethodsLoading = ref(false)
const paymentMethods = ref([])
const selectedPaymentChannel = ref(null)
const qrPayVisible = ref(false)
const qrCodeImage = ref('')
const activePayment = ref(null)
let quoteTimer = null
let paymentPollingTimer = null

const changeForm = reactive({
  change_type: 'spec',
  billing_cycle: 'monthly',
  requested_vcpu: undefined,
  requested_ram_mb: undefined,
  requested_disk_gb: undefined,
  requested_bandwidth_mbps: undefined,
  requested_ip_count: undefined,
  requirements: '',
})
const requestedRamGb = computed({
  get: () => (changeForm.requested_ram_mb ? mbToGb(changeForm.requested_ram_mb) : undefined),
  set: (gb) => { changeForm.requested_ram_mb = gbToMb(gb) },
})
const checkoutKind = ref('change')
const bwMode = ref('keep')
const bwDelta = ref(5)
const addIpCount = ref(0)
const releaseIpIds = ref([])
const changePhase = ref('form')
const changeSteps = ref([])
const changeResultMessage = ref('')

const onlinePaymentMethods = computed(() =>
  paymentMethods.value.filter((item) => item.online && item.channel_id))
const needsPayment = computed(() => (
  (changeForm.change_type === 'spec' || changeForm.change_type === 'renew' || changeForm.change_type === 'convert')
  && quote.value
  && Number(quote.value.due_now) > 0
))
const checkoutTitle = computed(() => {
  if (checkoutKind.value === 'convert') return '扫码支付转正式费用'
  if (checkoutKind.value === 'renew') return '扫码支付续费'
  return '扫码支付升配费用'
})
const checkoutHint = computed(() => {
  if (checkoutKind.value === 'convert') {
    return '支付完成后将转为正式使用，并写入正式开通日和到期日。'
  }
  if (checkoutKind.value === 'renew') {
    return '支付完成后将自动延长到期日，可在「我的服务」查看新的到期时间。'
  }
  return '支付完成后工单将发送到后台开通：资源充足则自动交付，不足则通知管理员处理。'
})
function daysUntil(value) {
  if (!value) return null
  const target = new Date(value)
  if (Number.isNaN(target.getTime())) return null
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const end = new Date(target.getFullYear(), target.getMonth(), target.getDate())
  return Math.round((end - start) / 86400000)
}
const dueReminders = computed(() => rows.value.filter((row) => {
  if (!row.expire_time || row.status === 'terminated') return false
  const days = daysUntil(row.expire_time)
  if (days == null || days < -1) return false
  return row.is_trial ? days <= 1 : days <= 3
}))
const deltaClass = computed(() => {
  const delta = Number(quote.value?.monthly_delta || 0)
  if (delta > 0) return 'up'
  if (delta < 0) return 'down'
  return ''
})
const quoteAlertType = computed(() => {
  const direction = quote.value?.direction
  if (direction === 'upgrade' || direction === 'ip_replace') return 'warning'
  if (direction === 'downgrade') return 'success'
  return 'info'
})
const submitButtonText = computed(() => {
  if (changeForm.change_type === 'terminate') return '提交终止申请'
  if (changeForm.change_type === 'renew') return needsPayment.value ? '确认续费并支付' : '确认续费'
  if (changeForm.change_type === 'convert') return needsPayment.value ? '确认转正式并支付' : '确认转正式'
  if (changeForm.change_type === 'replace_ip') return '提交替换申请'
  if (needsPayment.value) return '确认变更并支付'
  if (quote.value?.direction === 'downgrade') return '确认变更'
  if (quote.value?.direction === 'ip_replace') return '提交替换申请'
  return '确认变更'
})
const originalBandwidth = computed(() => Number(
  current.value?.spec_snapshot?.bandwidth_mbps
  || quote.value?.current_bandwidth_mbps
  || 0,
))
const targetBandwidth = computed(() => {
  const base = originalBandwidth.value
  const delta = Number(bwDelta.value || 0)
  if (bwMode.value === 'increase') return base + delta
  if (bwMode.value === 'decrease') return Math.max(0, base - delta)
  return base
})
const allocatedIps = computed(() => quote.value?.allocated_ips || [])
const currentAllocatedCount = computed(() => {
  if (quote.value) {
    const live = allocatedIps.value.length
    if (live > 0) return live
    return Number(quote.value.current_spec?.ip_count || current.value?.spec_snapshot?.ip_count || 0)
  }
  return Number(current.value?.spec_snapshot?.ip_count || 0)
})
const targetIpCount = computed(() => Math.max(
  0,
  currentAllocatedCount.value - releaseIpIds.value.length + Number(addIpCount.value || 0),
))

function specText(row) {
  const s = row?.spec_snapshot
  if (!s || typeof s !== 'object') return '-'
  const isEdge = row.service_type === 'edge'
  const parts = []
  if (!isEdge) {
    if (s.cpu_cores || s.vcpu) parts.push(`${s.cpu_cores || s.vcpu}核`)
    if (s.ram_mb) parts.push(ramText(s.ram_mb))
    if (s.disk_gb) parts.push(`${s.disk_gb}G`)
  }
  if (s.bandwidth_mbps) parts.push(`${s.bandwidth_mbps}M`)
  if (s.ip_count) parts.push(`${s.ip_count}IP`)
  return parts.length ? parts.join(' / ') : '-'
}

function buildSpecPayload() {
  const payload = {}
  if (changeForm.change_type === 'replace_ip') {
    payload.replace_ips = true
    if (changeForm.requested_ip_count != null) payload.requested_ip_count = changeForm.requested_ip_count
    return payload
  }
  if (current.value?.service_type !== 'edge') {
    if (changeForm.requested_vcpu != null) payload.requested_vcpu = changeForm.requested_vcpu
    if (changeForm.requested_ram_mb != null) payload.requested_ram_mb = changeForm.requested_ram_mb
    if (changeForm.requested_disk_gb != null) payload.requested_disk_gb = changeForm.requested_disk_gb
  }
  payload.requested_bandwidth_mbps = targetBandwidth.value
  payload.release_ip_ids = [...releaseIpIds.value]
  payload.add_ip_count = Number(addIpCount.value || 0)
  if (quote.value || payload.release_ip_ids.length || payload.add_ip_count) {
    payload.requested_ip_count = targetIpCount.value
  }
  return payload
}

function isIpReleased(id) {
  return releaseIpIds.value.includes(id)
}

function markReleaseIp(row) {
  if (!row?.id || isIpReleased(row.id)) return
  releaseIpIds.value = [...releaseIpIds.value, row.id]
}

function undoReleaseIp(row) {
  releaseIpIds.value = releaseIpIds.value.filter((id) => id !== row.id)
}

async function load() {
  loading.value = true
  try {
    const params = { page_size: 100 }
    if (statusFilter.value) params.status = statusFilter.value
    const res = await getServices(params)
    rows.value = res.results || []
  } finally {
    loading.value = false
  }
}

function changeDisabledReason(row) {
  if (!canChangeService.value) return '当前角色为只读，无法提交变更'
  if (row.status === 'terminated') return '已终止的服务不可变更'
  if (!row.can_change_request) return '该资源尚未关联服务实例，暂无法在线变更'
  return ''
}

function openManage(row) {
  current.value = row
  manageVisible.value = true
}

function openPay(row) {
  openChange(row, row.is_trial ? 'convert' : 'renew')
}

function openChange(row, preset) {
  current.value = row
  Object.assign(changeForm, {
    change_type: preset || 'spec',
    billing_cycle: 'monthly',
    requested_vcpu: row.spec_snapshot?.cpu_cores || row.spec_snapshot?.vcpu || undefined,
    requested_ram_mb: row.spec_snapshot?.ram_mb || undefined,
    requested_disk_gb: row.spec_snapshot?.disk_gb || undefined,
    requested_bandwidth_mbps: row.spec_snapshot?.bandwidth_mbps || undefined,
    requested_ip_count: row.spec_snapshot?.ip_count ?? undefined,
    requirements: '',
  })
  bwMode.value = 'keep'
  bwDelta.value = 5
  addIpCount.value = 0
  releaseIpIds.value = []
  changePhase.value = 'form'
  changeSteps.value = []
  changeResultMessage.value = ''
  quote.value = null
  selectedPaymentChannel.value = null
  changeVisible.value = true
  refreshQuote()
  loadPaymentMethods(row.fee_currency)
}

function resetChangeDialog() {
  quote.value = null
  selectedPaymentChannel.value = null
  paymentMethods.value = []
  bwMode.value = 'keep'
  bwDelta.value = 5
  addIpCount.value = 0
  releaseIpIds.value = []
  changePhase.value = 'form'
  changeSteps.value = []
  changeResultMessage.value = ''
  stopPaymentPolling()
}

async function loadPaymentMethods(currency) {
  paymentMethodsLoading.value = true
  paymentMethods.value = []
  selectedPaymentChannel.value = null
  try {
    const res = await getBillPaymentMethods({ currency })
    paymentMethods.value = res?.data || []
    selectedPaymentChannel.value = onlinePaymentMethods.value[0]?.channel_id || null
  } catch {
    paymentMethods.value = []
  } finally {
    paymentMethodsLoading.value = false
  }
}

async function refreshQuote() {
  if (!current.value?.instance_id) {
    quote.value = null
    return
  }
  if (changeForm.change_type === 'renew' || changeForm.change_type === 'convert') {
    quoting.value = true
    try {
      const quoteApi = changeForm.change_type === 'convert' ? quoteTrialConvert : quoteServiceRenew
      const res = await quoteApi(current.value.instance_id, {
        billing_cycle: changeForm.billing_cycle,
      })
      quote.value = res?.data || res
      await loadPaymentMethods(quote.value.currency || current.value.fee_currency)
    } catch (error) {
      quote.value = null
      ElMessage.warning(error?.response?.data?.message || error?.message || '续费报价失败')
    } finally {
      quoting.value = false
    }
    return
  }
  if (changeForm.change_type !== 'spec' && changeForm.change_type !== 'replace_ip') {
    quote.value = null
    return
  }
  quoting.value = true
  try {
    const res = await quoteServiceChange(current.value.instance_id, buildSpecPayload())
    quote.value = res?.data || res
    if (needsPayment.value) {
      await loadPaymentMethods(quote.value.currency || current.value.fee_currency)
    }
  } catch (error) {
    quote.value = null
    ElMessage.warning(error?.response?.data?.message || error?.message || '报价失败')
  } finally {
    quoting.value = false
  }
}

function scheduleQuote() {
  if (quoteTimer) window.clearTimeout(quoteTimer)
  quoteTimer = window.setTimeout(() => {
    void refreshQuote()
  }, 280)
}

watch(
  () => [
    changeForm.change_type,
    changeForm.billing_cycle,
    changeForm.requested_vcpu,
    changeForm.requested_ram_mb,
    changeForm.requested_disk_gb,
    changeForm.requested_bandwidth_mbps,
    changeForm.requested_ip_count,
    bwMode.value,
    bwDelta.value,
    addIpCount.value,
    releaseIpIds.value.join(','),
  ],
  () => {
    if (changeVisible.value && ['spec', 'replace_ip', 'renew', 'convert'].includes(changeForm.change_type)) {
      scheduleQuote()
    }
  },
)

async function submitChange() {
  if (!current.value?.instance_id) {
    ElMessage.warning('该资源尚未关联服务实例，请通过管理面板或联系客服变更')
    return
  }

  const payload = {
    requirements: changeForm.requirements || '',
  }

  if (changeForm.change_type === 'renew' || changeForm.change_type === 'convert') {
    payload.billing_cycle = changeForm.billing_cycle
    if (needsPayment.value) {
      if (!selectedPaymentChannel.value) {
        ElMessage.warning('请选择支付渠道')
        return
      }
      payload.channel_id = selectedPaymentChannel.value
      const method = onlinePaymentMethods.value.find((m) => m.channel_id === selectedPaymentChannel.value)
      if (method?.provider) payload.payment_method = method.provider
    }
  } else if (changeForm.change_type === 'terminate') {
    payload.change_type = changeForm.change_type
  } else {
    Object.assign(payload, buildSpecPayload())
    if (quote.value?.direction === 'unchanged' && changeForm.change_type !== 'replace_ip') {
      ElMessage.warning('规格未发生变化。协议或接口参数请到「管理」页配置。')
      return
    }
    if (needsPayment.value) {
      if (!selectedPaymentChannel.value) {
        ElMessage.warning('请选择支付渠道')
        return
      }
      payload.channel_id = selectedPaymentChannel.value
      const method = onlinePaymentMethods.value.find((m) => m.channel_id === selectedPaymentChannel.value)
      if (method?.provider) payload.payment_method = method.provider
    }
  }

  submitting.value = true
  try {
    const isRenew = changeForm.change_type === 'renew'
    const isConvert = changeForm.change_type === 'convert'
    const res = isConvert
      ? await convertTrialService(current.value.instance_id, payload)
      : isRenew
        ? await renewService(current.value.instance_id, payload)
        : await requestServiceChange(current.value.instance_id, payload)
    const data = res?.data || {}
    checkoutKind.value = isConvert ? 'convert' : (isRenew ? 'renew' : 'change')
    await load()

    if (data.checkout) {
      changeVisible.value = false
      ElMessage.success(res?.message || (isConvert ? '转正式账单已创建，请完成支付' : isRenew ? '续费账单已创建，请完成支付' : '变更已提交，请完成支付'))
      await handleCheckout(data)
      return
    }
    if (data.payment_required && data.billing?.id) {
      changeVisible.value = false
      ElMessage.info(isConvert
        ? '转正式账单已创建，请前往账单支付，付款后写入正式开通日和到期日'
        : isRenew
          ? '续费账单已创建，请前往账单支付，付款后将自动延长到期日'
          : '变更已提交，请前往账单支付对应费用，付款后将自动开通')
      router.push({ name: 'bills' })
      return
    }
    if (!isRenew && changeForm.change_type === 'spec') {
      changePhase.value = 'result'
      changeSteps.value = data.progress_steps?.length
        ? data.progress_steps
        : [{ key: 'activate', label: '变更生效', status: 'done', detail: res?.message || '变更成功' }]
      changeResultMessage.value = res?.message || '变更成功'
      ElMessage.success(changeResultMessage.value)
      return
    }
    changeVisible.value = false
    await reportChangeResult(
      data.order?.id,
      res?.message || (isRenew ? '续费已提交' : '变更成功'),
    )
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

async function reportChangeResult(orderId, prefix = '变更已提交') {
  if (!orderId) {
    ElMessage.success(prefix)
    return
  }
  let order = null
  for (let i = 0; i < 6; i += 1) {
    try {
      order = await getOrder(orderId)
    } catch {
      break
    }
    const state = order?.auto_provision_status
    if (state === 'success') {
      ElMessage.success(
        checkoutKind.value === 'convert'
          ? `${prefix}，已转为正式使用`
          : checkoutKind.value === 'renew' || prefix.includes('续费')
            ? `${prefix}，服务到期日已延长`
            : `${prefix}，服务已自动开通并完成交付`,
      )
      return
    }
    if (state === 'insufficient') {
      ElMessage.warning(order.auto_provision_message || `${prefix}，当前节点资源不足，已通知管理员补齐后手动交付`)
      return
    }
    if (state === 'paid_pending') {
      ElMessage.info(order.auto_provision_message || `${prefix}，支付已确认，等待管理员手动交付`)
      return
    }
    if (state === 'failed') {
      ElMessage.warning(order.auto_provision_message || `${prefix}，自动开通失败，已通知管理员处理`)
      return
    }
    await sleep(700)
  }
  ElMessage.success(`${prefix}，工单已进入开通流程，可在「我的订单」查看进度`)
}

async function handleCheckout(data) {
  const checkout = data.checkout || {}
  activePayment.value = {
    ...(data.transaction || {}),
    order_id: data.order?.id,
    amount: data.transaction?.amount || data.billing?.amount,
    currency: data.transaction?.currency || data.billing?.currency || quote.value?.currency,
  }
  if (!checkout.mode && !(checkout.url || checkout.redirect_url || checkout.form_action)) {
    router.push({ name: 'bills' })
    return
  }
  try {
    await launchCheckout(checkout, {
      onQr: async (payload) => {
        qrCodeImage.value = payload.qr_code_url || await QRCode.toDataURL(payload.qr_code_text, { width: 220 })
        qrPayVisible.value = true
        startPaymentPolling()
      },
      onSdk: async () => {
        ElMessage.info('请按支付渠道提示完成支付，可在账单中查看进度')
        router.push({ name: 'bills' })
      },
    })
  } catch {
    ElMessage.warning('未返回有效支付页面，请前往账单继续支付')
    router.push({ name: 'bills' })
  }
}

function stopPaymentPolling() {
  if (paymentPollingTimer) {
    window.clearInterval(paymentPollingTimer)
    paymentPollingTimer = null
  }
}

function startPaymentPolling() {
  stopPaymentPolling()
  paymentPollingTimer = window.setInterval(refreshPaymentStatus, 3000)
}

async function refreshPaymentStatus() {
  const transactionNo = activePayment.value?.transaction_no
  if (!transactionNo) return
  try {
    const payment = await getPaymentTransaction(transactionNo)
    activePayment.value = { ...activePayment.value, ...payment }
    if (['succeeded', 'paid', 'success'].includes(String(payment.status || '').toLowerCase())) {
      stopPaymentPolling()
      qrPayVisible.value = false
      await reportChangeResult(activePayment.value?.order_id, '支付成功')
      load()
    }
  } catch {
    // 轮询失败忽略，等待下一次
  }
}

onMounted(load)
onBeforeUnmount(() => {
  if (quoteTimer) window.clearTimeout(quoteTimer)
  stopPaymentPolling()
})
</script>

<style scoped>
.services {
  min-width: 0;
}
.paid-alert {
  margin-bottom: 14px;
}
.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  flex-wrap: wrap;
  gap: 12px;
}
.sm {
  font-size: 12px;
}
.services-table {
  width: 100%;
}
.row3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.mb {
  margin-bottom: 14px;
}
.mt {
  margin-top: 10px;
}
.quote-box {
  margin: 4px 0 16px;
  padding: 14px;
  border: 1px solid var(--ce-border, #e5e7eb);
  border-radius: 12px;
  background: var(--ce-surface, #f8fafc);
}
.quote-title {
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ce-text, #111827);
}
.quote-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.quote-item {
  min-width: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #eef2f7;
}
.quote-item span {
  display: block;
  color: #6b7280;
  font-size: 12px;
}
.quote-item strong {
  display: block;
  margin-top: 4px;
  font-size: 16px;
  color: #111827;
}
.quote-item strong.accent {
  color: #2563eb;
}
.quote-item strong.up {
  color: #dc2626;
}
.quote-item strong.down {
  color: #059669;
}
.quote-meta {
  margin-top: 10px;
  color: #6b7280;
  font-size: 12px;
}
.payment-methods {
  width: 100%;
}
.payment-radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.payment-radio {
  margin-right: 0;
}
.qr-payment {
  text-align: center;
}
.qr-payment img {
  width: 220px;
  height: 220px;
  margin: 0 auto 12px;
}
.qr-status {
  color: #6b7280;
  font-size: 13px;
}
.ml-tag {
  margin-left: 4px;
}
.origin-box,
.ip-box {
  margin: 0 0 16px;
  padding: 14px;
  border: 1px solid var(--ce-border, #e5e7eb);
  border-radius: 12px;
  background: #fff;
}
.origin-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.origin-grid span {
  display: block;
  color: #6b7280;
  font-size: 12px;
}
.origin-grid strong {
  display: block;
  margin-top: 2px;
  font-size: 14px;
}
.target-bw {
  min-height: 32px;
  display: flex;
  align-items: center;
  font-size: 20px;
  font-weight: 700;
  color: #2563eb;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.released {
  text-decoration: line-through;
  color: #9ca3af;
}
.push-steps {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.push-step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  font-size: 13px;
}
.push-step.done {
  border-color: #b3e19d;
  background: #f0f9eb;
}
.push-step.error {
  border-color: #fab6b6;
  background: #fef0f0;
}
.push-step.warn {
  border-color: #f3d19e;
  background: #fdf6ec;
}
.push-label {
  font-weight: 600;
}
.push-detail {
  color: #909399;
  margin-top: 2px;
}
@media (max-width: 640px) {
  .row3,
  .row2,
  .quote-grid,
  .origin-grid {
    grid-template-columns: 1fr;
  }
}
</style>
