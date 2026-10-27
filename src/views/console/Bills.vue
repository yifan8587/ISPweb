<template>
  <div class="bills">
    <div class="bar">
      <div>
        <h3 style="margin:0">账单中心</h3>
        <p class="wallet-hint">账户余额 {{ money(wallet.balance, wallet.currency) }}</p>
      </div>
      <div class="bar-actions">
        <el-button v-if="caps.billing_pay" type="primary" @click="openRecharge">余额充值</el-button>
        <el-radio-group v-model="statusFilter" @change="onFilterChange">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="unpaid">待支付</el-radio-button>
          <el-radio-button label="paid">已支付</el-radio-button>
          <el-radio-button label="overdue">逾期</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <el-table :data="rows" v-loading="loading" stripe border row-key="id"
              :expand-row-keys="expanded" @expand-change="onExpand">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="items">
            <el-table :data="row.items" size="small" border>
              <el-table-column prop="instance_no" label="实例编号" width="150" />
              <el-table-column prop="description" label="计费说明" min-width="180" />
              <el-table-column label="业务类型" width="100">
                <template #default="{ row: it }">{{ it.service_type_label || serviceTypeLabel[it.service_type] || it.service_type || '—' }}</template>
              </el-table-column>
              <el-table-column prop="product_name" label="产品" width="130" />
              <el-table-column label="计费周期" width="200">
                <template #default="{ row: it }">
                  {{ formatDate(it.period_start) }} ~ {{ formatDate(it.period_end) }}
                  <el-tag v-if="it.is_trial" size="small" type="info" effect="plain">测试</el-tag>
                  <el-tag v-else-if="it.is_prorated" size="small" type="warning" effect="plain">{{ it.days_used }}/{{ it.days_in_month }}天</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="基础" width="100">
                <template #default="{ row: it }">{{ money(it.base_monthly_fee, it.source_currency || row.currency) }}</template>
              </el-table-column>
              <el-table-column label="超出" width="100">
                <template #default="{ row: it }">{{ money(it.overage_monthly_fee, it.source_currency || row.currency) }}</template>
              </el-table-column>
              <el-table-column label="结算金额" width="110">
                <template #default="{ row: it }">
                  <b>{{ money(it.amount, it.currency || row.currency) }}</b>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="90" fixed="right">
                <template #default="{ row: it }">
                  <el-button link type="primary" size="small" @click="openItemDetail(it, row.currency)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="bill_no" label="账单编号" width="160" />
      <el-table-column prop="bill_month" label="账单月份" width="110" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">{{ row.billing_kind_label || '月结' }}</template>
      </el-table-column>
      <el-table-column label="优惠前金额" width="125">
        <template #default="{ row }">{{ money(row.gross_amount || row.amount, row.currency) }}</template>
      </el-table-column>
      <el-table-column label="推广优惠" width="145">
        <template #default="{ row }">
          <template v-if="Number(row.promotion_discount_amount || 0) > 0">
            <span class="discount">-{{ money(row.promotion_discount_amount, row.currency) }}</span>
            <small class="promo-code">{{ row.promotion_code }}</small>
          </template>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="应付金额" width="120">
        <template #default="{ row }"><b>{{ money(row.amount, row.currency) }}</b></template>
      </el-table-column>
      <el-table-column label="已付 / 待付" width="170">
        <template #default="{ row }">
          <span class="muted">{{ money(row.paid_amount, row.currency) }}</span> /
          <span :class="{ owe: Number(row.outstanding_amount) > 0 }">{{ money(row.outstanding_amount, row.currency) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="billStatusTag[row.status]?.type || 'info'">
            {{ row.status_label || billStatusTag[row.status]?.label || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="支付方式" width="110">
        <template #default="{ row }">
          {{ row.payment_method_label || paymentMethodLabel[row.payment_method] || (row.payment_method ? row.payment_method : '—') }}
        </template>
      </el-table-column>
      <el-table-column label="到期日" width="110">
        <template #default="{ row }">{{ formatDate(row.due_date) }}</template>
      </el-table-column>
      <el-table-column label="支付时间" width="110">
        <template #default="{ row }">{{ row.paid_at ? formatDate(row.paid_at, true) : '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="canPay(row)"
            type="primary"
            link
            size="small"
            @click="openPay(row)"
          >支付</el-button>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager" v-if="total > pageSize">
      <el-pagination
        background
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        v-model:current-page="page"
        @current-change="load"
      />
    </div>

    <el-empty v-if="!loading && !rows.length" description="暂无账单" />

    <el-dialog v-model="rechargeVisible" title="余额充值" width="420px" destroy-on-close>
      <p class="muted">充值会生成一张待支付账单，需用在线支付完成，不能用余额循环充值。</p>
      <el-form label-position="top" style="margin-top:12px">
        <el-form-item label="充值金额">
          <el-input-number
            v-model="rechargeAmount"
            :min="1"
            :max="100000"
            :precision="2"
            :step="10"
            style="width:100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rechargeVisible = false">取消</el-button>
        <el-button type="primary" :loading="recharging" :disabled="!rechargeAmount" @click="submitRecharge">
          创建充值账单
        </el-button>
      </template>
    </el-dialog>

    <!-- 选择支付方式 -->
    <el-dialog v-model="payVisible" title="账单支付" width="480px" destroy-on-close @closed="resetPay">
      <template v-if="payRow">
        <div class="pay-summary">
          <div class="pay-row"><span>账单编号</span><b>{{ payRow.bill_no }}</b></div>
          <div class="pay-row"><span>账单月份</span><b>{{ payRow.bill_month }}</b></div>
          <div v-if="Number(payRow.promotion_discount_amount || 0) > 0" class="pay-row">
            <span>推广优惠</span>
            <b class="discount">-{{ money(payRow.promotion_discount_amount, payRow.currency) }}（{{ payRow.promotion_code }}）</b>
          </div>
          <div class="pay-row"><span>待付金额</span><b class="owe">{{ money(payRow.outstanding_amount, payRow.currency) }}</b></div>
        </div>
        <el-form label-position="top" style="margin-top:12px">
          <el-form-item label="支付方式">
            <div class="pay-methods">
              <div
                v-for="m in visiblePayMethods"
                :key="paymentMethodKey(m)"
                class="pay-method-card"
                :class="{ active: selectedMethod === paymentMethodKey(m), disabled: m.available === false }"
                @click="m.available === false ? null : (selectedMethod = paymentMethodKey(m))"
              >
                <span class="pm-label">{{ m.label }}{{ m.reputation && m.balance != null ? `（余额 ${m.balance}）` : '' }}</span>
                <span class="pm-tag">{{ m.reputation ? (m.available === false ? '余额不足' : '信誉值') : (m.online ? '在线' : '线下') }}</span>
              </div>
            </div>
          </el-form-item>
          <el-form-item v-if="selectedMethodInfo && !selectedMethodInfo.online && !selectedMethodInfo.wallet" label="支付金额">
            <el-input-number
              v-model="payAmount"
              :min="0.01"
              :max="Number(payRow.outstanding_amount)"
              :precision="2"
              :step="1"
              style="width:100%"
            />
          </el-form-item>
          <el-alert v-if="selectedMethod === 'bank_transfer'" type="info" :closable="false" show-icon
                    title="请转账至公司对公账户，转账备注填写账单编号，确认后提交。" />
          <el-alert v-if="selectedMethod === 'cash'" type="info" :closable="false" show-icon
                    title="现金支付需线下交付后在此确认登记。" />
        </el-form>
      </template>
      <template #footer>
        <el-button @click="payVisible = false">取消</el-button>
        <el-button type="primary" :loading="paying" :disabled="!selectedMethod" @click="submitPay">
          {{ selectedMethodInfo?.wallet ? '余额支付' : (selectedMethodInfo?.reputation ? '信誉值支付' : (selectedMethodInfo?.online ? '前往支付' : '确认支付')) }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 在线支付：二维码由服务端真实网关指令生成，支付状态由验签回调确认。 -->
    <el-dialog v-model="onlineVisible" :title="onlineTitle" width="420px" destroy-on-close @closed="resetOnline">
      <div v-if="onlineSession" class="online-pay">
        <div class="online-amount">
          <span>应付金额</span>
          <b>{{ money(onlineSession.amount, onlineSession.currency) }}</b>
        </div>
        <div class="qr-box">
          <img v-if="qrCodeImage" :src="qrCodeImage" alt="支付二维码" class="qr-image">
          <el-skeleton v-else :rows="4" animated />
          <p class="qr-tip">请使用 {{ selectedMethodInfo?.label || '支付应用' }} 完成扫码支付</p>
        </div>
        <el-alert type="info" :closable="false" show-icon
                  title="支付完成后将由支付渠道验签回调自动更新账单状态。" />
      </div>
      <template #footer>
        <el-button @click="onlineVisible = false">稍后查看账单</el-button>
      </template>
    </el-dialog>

    <!-- 计费明细详情 -->
    <el-dialog v-model="detailVisible" title="计费明细" width="720px" destroy-on-close>
      <template v-if="detailRow">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="实例编号">{{ detailRow.instance_no || '—' }}</el-descriptions-item>
          <el-descriptions-item label="业务类型">{{ detailRow.service_type_label || serviceTypeLabel[detailRow.service_type] || '—' }}</el-descriptions-item>
          <el-descriptions-item label="计费项">{{ detailRow.description }}</el-descriptions-item>
          <el-descriptions-item label="关联产品">{{ detailRow.product_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="计费依据">{{ detailRow.detail?.basis_label || '—' }}</el-descriptions-item>
          <el-descriptions-item label="计费周期">{{ formatDate(detailRow.period_start) }} ~ {{ formatDate(detailRow.period_end) }}</el-descriptions-item>
          <el-descriptions-item label="计费方式">
            <el-tag v-if="detailRow.is_trial" size="small" type="info">测试（未计费）</el-tag>
            <el-tag v-else-if="detailRow.is_prorated" size="small" type="warning">按天比例</el-tag>
            <el-tag v-else size="small" type="success">整月</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="使用天数">{{ detailRow.days_used }} / {{ detailRow.days_in_month }} 天</el-descriptions-item>
        </el-descriptions>

        <template v-if="detailRow.detail?.spec_dims?.length">
          <el-divider content-position="left">规格对比（实际 vs 模版基准）</el-divider>
          <el-table :data="detailRow.detail.spec_dims" size="small" border>
            <el-table-column prop="label" label="资源项" width="120" />
            <el-table-column label="模版基准" align="right">
              <template #default="{ row }">{{ row.base }} {{ row.unit }}</template>
            </el-table-column>
            <el-table-column label="实际分配" align="right">
              <template #default="{ row }">{{ row.actual }} {{ row.unit }}</template>
            </el-table-column>
            <el-table-column label="超出" align="right">
              <template #default="{ row }">
                <span v-if="row.over > 0" class="overage-text">+{{ row.over }} {{ row.unit }}</span>
                <span v-else style="color:#67c23a">0</span>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <template v-if="detailRow.detail?.overage_items?.length">
          <el-divider content-position="left">超出部分阶梯计价</el-divider>
          <el-table :data="detailRow.detail.overage_items" size="small" border>
            <el-table-column prop="label" label="资源项" width="120" />
            <el-table-column prop="upgrade_qty" label="超出单位数" align="right" />
            <el-table-column label="月租增量" align="right">
              <template #default="{ row }">+{{ curSym(detailRow.source_currency) }}{{ Number(row.monthly_delta).toFixed(2) }}</template>
            </el-table-column>
          </el-table>
        </template>

        <el-divider content-position="left">计费汇总</el-divider>
        <div class="calc-box">
          <div class="calc-row">
            <span>产品基础月租</span>
            <span>{{ curSym(detailRow.source_currency) }}{{ Number(detailRow.base_monthly_fee).toFixed(2) }}</span>
          </div>
          <div class="calc-row">
            <span>超出部分月租</span>
            <span :class="{ 'overage-text': Number(detailRow.overage_monthly_fee) > 0 }">
              +{{ curSym(detailRow.source_currency) }}{{ Number(detailRow.overage_monthly_fee).toFixed(2) }}
            </span>
          </div>
          <div class="calc-row calc-sub">
            <span>整月单价（基础 + 超出）</span>
            <span>{{ curSym(detailRow.source_currency) }}{{ Number(detailRow.unit_monthly_fee).toFixed(2) }}</span>
          </div>
          <div class="calc-row" v-if="detailRow.is_prorated">
            <span>× 按天比例（{{ detailRow.days_used }}/{{ detailRow.days_in_month }}）</span>
            <span>× {{ detailRow.detail?.ratio || (detailRow.days_used / detailRow.days_in_month).toFixed(4) }}</span>
          </div>
          <div class="calc-row calc-sub">
            <span>原始金额</span>
            <span>{{ curSym(detailRow.source_currency) }}{{ Number(detailRow.amount_original).toFixed(2) }}</span>
          </div>
          <div class="calc-row" v-if="detailRow.source_currency !== detailRow.currency">
            <span>× 折算汇率（{{ detailRow.source_currency }} → {{ detailRow.currency }}）</span>
            <span>× {{ detailRow.exchange_rate }}</span>
          </div>
          <div class="calc-row calc-total">
            <span>结算金额{{ detailRow.is_trial ? '（测试，不计入账单）' : '' }}</span>
            <span>{{ curSym(detailRow.currency) }}{{ Number(detailRow.amount).toFixed(2) }}</span>
          </div>
        </div>
      </template>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import QRCode from 'qrcode'
import { ElMessage } from 'element-plus'
import {
  createRechargeBill,
  getBillPaymentMethods,
  getBills,
  getPaymentTransaction,
  getWallet,
  payBill,
  payBillWithBalance,
} from '@/api'
import { useCapabilities } from '@/composables/useCapabilities'
import { launchCheckout } from '@/utils/checkout'
import { AIRWALLEX_ELEMENTS_SDK, loadLocalScript } from '@/utils/vendorAssets'
import { billStatusTag, curSym, formatDate, money, paymentMethodLabel, serviceTypeLabel } from '@/utils/format'

const { caps } = useCapabilities()
const route = useRoute()
const rows = ref([])
const wallet = ref({ balance: 0, currency: 'USD', ledgers: [] })
const rechargeVisible = ref(false)
const rechargeAmount = ref(100)
const recharging = ref(false)
const loading = ref(false)
const paying = ref(false)
const statusFilter = ref('')
const expanded = ref([])
const page = ref(1)
const pageSize = 20
const total = ref(0)

const paymentMethods = ref([])
const payVisible = ref(false)
const payRow = ref(null)
const selectedMethod = ref('')
const payAmount = ref(0)

const onlineVisible = ref(false)
const onlineSession = ref(null)
const qrCodeImage = ref('')

const detailVisible = ref(false)
const detailRow = ref(null)

function paymentMethodKey(method) {
  if (method.wallet) return 'balance'
  return method.online ? `online:${method.channel_id}` : method.value
}

const canUseWalletPay = computed(() => {
  const row = payRow.value
  if (!row || !caps.value.billing_pay) return false
  if (row.billing_kind === 'wallet_recharge') return false
  if (!['unpaid', 'overdue'].includes(row.status)) return false
  if (Number(row.outstanding_amount) <= 0) return false
  const billCur = String(row.currency || 'USD').toUpperCase()
  const walletCur = String(wallet.value.currency || 'USD').toUpperCase()
  return billCur === walletCur && Number(wallet.value.balance) > 0
})

const visiblePayMethods = computed(() => {
  const list = [...paymentMethods.value]
  if (canUseWalletPay.value) {
    list.unshift({
      value: 'balance',
      label: `账户余额（${money(wallet.value.balance, wallet.value.currency)}）`,
      online: false,
      wallet: true,
    })
  }
  return list
})

const selectedMethodInfo = computed(() =>
  visiblePayMethods.value.find((m) => paymentMethodKey(m) === selectedMethod.value))

const onlineTitle = computed(() =>
  onlineSession.value ? `${selectedMethodInfo.value?.label || '在线支付'} · 支付中` : '在线支付')

function canPay(row) {
  return caps.value.billing_pay
    && ['unpaid', 'overdue'].includes(row.status)
    && Number(row.outstanding_amount) > 0
}

function onExpand(row, expandedRows) {
  expanded.value = expandedRows.map((r) => r.id)
}

function onFilterChange() {
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (statusFilter.value) params.status = statusFilter.value
    const res = await getBills(params)
    rows.value = res.results || []
    total.value = res.count || rows.value.length
  } finally {
    loading.value = false
  }
}

async function loadWallet() {
  try {
    const res = await getWallet()
    wallet.value = res.data || { balance: 0, currency: 'USD', ledgers: [] }
  } catch {
    wallet.value = { balance: 0, currency: 'USD', ledgers: [] }
  }
}

function openRecharge() {
  rechargeAmount.value = 100
  rechargeVisible.value = true
}

async function submitRecharge() {
  if (!rechargeAmount.value) return
  recharging.value = true
  try {
    const res = await createRechargeBill({ amount: rechargeAmount.value })
    const billing = res.data
    rechargeVisible.value = false
    ElMessage.success('充值账单已创建，请完成在线支付')
    await load()
    if (billing) await openPay(billing)
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.response?.data?.detail || '创建充值账单失败')
  } finally {
    recharging.value = false
  }
}

async function loadPaymentMethods(currency = 'USD', extra = {}) {
  try {
    const res = await getBillPaymentMethods({ currency, ...extra })
    paymentMethods.value = res.data || []
  } catch {
    paymentMethods.value = []
  }
}

async function openPay(row) {
  payRow.value = row
  selectedMethod.value = ''
  payAmount.value = Number(row.outstanding_amount)
  payVisible.value = true
  const productId = row.items?.find((item) => item.product)?.product
  await Promise.all([
    loadPaymentMethods(row.currency, {
      billing_id: row.id,
      ...(productId ? { product_id: productId } : {}),
    }),
    loadWallet(),
  ])
}

function resetPay() {
  payRow.value = null
  selectedMethod.value = ''
  payAmount.value = 0
}

function resetOnline() {
  stopPaymentPolling()
  onlineSession.value = null
  qrCodeImage.value = ''
}

function openItemDetail(item) {
  detailRow.value = item
  detailVisible.value = true
}

function updateRowInList(updated) {
  const idx = rows.value.findIndex((r) => r.id === updated.id)
  if (idx >= 0) rows.value[idx] = updated
}

async function launchAirwallex(checkout) {
  const payload = checkout.sdk_payload || {}
  await loadLocalScript(AIRWALLEX_ELEMENTS_SDK)
  const sdk = window.AirwallexComponentsSDK
  if (!sdk?.init) throw new Error('Airwallex 收银台未正确加载')
  const { payments } = await sdk.init({ env: payload.env, enabledElements: ['payments'] })
  if (!payments?.redirectToCheckout) throw new Error('Airwallex 收银台不可用')
  await payments.redirectToCheckout({
    env: payload.env,
    mode: 'payment',
    currency: payload.currency,
    country_code: payload.country_code,
    intent_id: payload.intent_id,
    client_secret: payload.client_secret,
    successUrl: payload.success_url,
  })
}

let paymentPollingTimer = null

function stopPaymentPolling() {
  if (paymentPollingTimer) {
    window.clearInterval(paymentPollingTimer)
    paymentPollingTimer = null
  }
}

function startPaymentPolling() {
  stopPaymentPolling()
  paymentPollingTimer = window.setInterval(refreshOnlinePayment, 3000)
}

async function refreshOnlinePayment() {
  const transactionNo = onlineSession.value?.transaction_no
  if (!transactionNo) return
  try {
    const payment = await getPaymentTransaction(transactionNo)
    onlineSession.value = payment
    if (payment.status === 'succeeded') {
      stopPaymentPolling()
      onlineVisible.value = false
      ElMessage.success('支付成功，账单状态已更新')
      await Promise.all([load(), loadWallet()])
    } else if (['failed', 'cancelled', 'expired'].includes(payment.status)) {
      stopPaymentPolling()
      ElMessage.error(payment.failure_reason || '支付未成功，请重新发起支付')
    }
  } catch {
    // 网络短暂异常时下一轮继续查询。
  }
}

async function handleOnlineCheckout(checkout, transaction) {
  onlineSession.value = transaction
  await launchCheckout(checkout, {
    onQr: async (payload) => {
      qrCodeImage.value = payload.qr_code_url || await QRCode.toDataURL(payload.qr_code_text, {
        width: 240,
        margin: 1,
        errorCorrectionLevel: 'M',
      })
      onlineVisible.value = true
      startPaymentPolling()
    },
    onSdk: async (payload) => {
      if (payload.sdk === 'airwallex') {
        await launchAirwallex(payload)
        return
      }
      ElMessage.info('请按支付渠道提示完成支付')
    },
  })
}

async function submitPay() {
  if (!payRow.value || !selectedMethod.value || !selectedMethodInfo.value) return
  paying.value = true
  try {
    const method = selectedMethodInfo.value
    if (method.wallet) {
      const res = await payBillWithBalance(payRow.value.id)
      updateRowInList(res.data)
      payVisible.value = false
      ElMessage.success('余额支付成功')
      await Promise.all([load(), loadWallet()])
      return
    }
    if (method.reputation) {
      if (method.available === false) {
        ElMessage.warning(method.disabled_reason || '信誉值余额不足')
        return
      }
      const res = await payBill(payRow.value.id, { payment_method: 'reputation' })
      updateRowInList(res.data)
      payVisible.value = false
      ElMessage.success('信誉值支付成功')
      await Promise.all([load(), loadWallet()])
      return
    }
    if (method.online) {
      const initRes = await payBill(payRow.value.id, {
        payment_method: method.value,
        channel_id: method.channel_id,
        step: 'init',
      })
      payVisible.value = false
      await handleOnlineCheckout(initRes.data?.checkout || {}, {
        transaction_no: initRes.data?.transaction_no,
        status: initRes.data?.status,
        amount: payRow.value.outstanding_amount,
        currency: payRow.value.currency,
      })
      return
    }
    const res = await payBill(payRow.value.id, {
      payment_method: method.value,
      step: 'confirm',
      amount: payAmount.value,
    })
    updateRowInList(res.data)
    payVisible.value = false
    ElMessage.success('支付成功，账单状态已更新')
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.response?.data?.detail || error?.message || '支付失败')
  } finally {
    paying.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadPaymentMethods(), load(), loadWallet()])
  if (route.query.recharge && caps.value.billing_pay) openRecharge()
})

onBeforeUnmount(stopPaymentPolling)
</script>

<style scoped>
.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  flex-wrap: wrap;
  gap: 12px;
}
.bar-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.wallet-hint {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--ce-muted);
}
.items {
  padding: 12px 18px;
  background: var(--ce-bg);
}
.owe {
  color: #ef4444;
  font-weight: 600;
}
.muted {
  color: var(--ce-muted);
}
.discount {
  color: #16a34a;
  font-weight: 600;
}
.promo-code {
  display: block;
  margin-top: 2px;
  color: var(--ce-muted);
  font-size: 11px;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.pay-summary {
  background: var(--ce-bg);
  border-radius: 10px;
  padding: 12px 14px;
}
.pay-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 14px;
}
.pay-row span {
  color: var(--ce-muted);
}
.pay-methods {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  width: 100%;
}
.pay-method-card {
  border: 1px solid var(--el-border-color);
  border-radius: 10px;
  padding: 12px 14px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: border-color 0.2s, background 0.2s;
}
.pay-method-card:hover {
  border-color: var(--ce-primary);
}
.pay-method-card.active {
  border-color: var(--ce-primary);
  background: #eff6ff;
}
.pay-method-card.disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.pay-method-card.disabled:hover {
  border-color: var(--el-border-color);
}
.pm-label {
  font-weight: 600;
  font-size: 14px;
}
.pm-tag {
  font-size: 12px;
  color: var(--ce-muted);
}
.online-pay {
  text-align: center;
}
.online-amount {
  margin-bottom: 16px;
}
.online-amount span {
  display: block;
  color: var(--ce-muted);
  font-size: 13px;
  margin-bottom: 4px;
}
.online-amount b {
  font-size: 28px;
  color: #ef4444;
}
.qr-box {
  margin: 12px 0 16px;
}
.qr-image {
  display: block;
  width: 240px;
  height: 240px;
  margin: 0 auto;
}
.qr-tip {
  margin-top: 10px;
  font-size: 13px;
  color: var(--ce-muted);
}
.calc-box {
  background: var(--ce-bg);
  border-radius: 10px;
  padding: 12px 14px;
}
.calc-row {
  display: flex;
  justify-content: space-between;
  padding: 5px 0;
  font-size: 13px;
}
.calc-sub {
  color: var(--ce-muted);
  border-top: 1px dashed var(--el-border-color);
  margin-top: 4px;
  padding-top: 8px;
}
.calc-total {
  font-weight: 700;
  font-size: 15px;
  border-top: 1px solid var(--el-border-color);
  margin-top: 8px;
  padding-top: 10px;
}
.overage-text {
  color: #d97706;
  font-weight: 600;
}
@media (max-width: 640px) {
  .pay-methods { grid-template-columns: 1fr; }
  .qr-image {
    width: min(240px, 70vw);
    height: auto;
  }
}
</style>
