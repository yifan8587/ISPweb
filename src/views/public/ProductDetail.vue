<template>
  <div class="detail-page" v-loading="loading">
    <div class="ce-container" v-if="product">
      <div class="bread">
        <router-link to="/products">全部产品</router-link>
        <el-icon><ArrowRight /></el-icon>
        <span>{{ categoryLabel(product) }}{{ regionText !== '-' ? ` · ${regionText}` : '' }}</span>
      </div>

      <div class="detail-grid">
        <div class="main ce-card">
          <div class="main-head">
            <el-tag :type="product.category === 'vps' ? 'primary' : 'success'" effect="dark" round>
              {{ categoryLabel(product) }}
            </el-tag>
            <span v-if="isHot" class="hot-badge">🔥 热卖</span>
            <span class="head-loc">{{ regionText }}</span>
          </div>

          <h3 class="blk-title">规格配置</h3>
          <div class="spec-grid">
            <template v-if="product.category === 'vps'">
              <div class="spec-item"><span>vCPU</span><b>{{ product.cpu_cores }} 核</b></div>
              <div class="spec-item"><span>内存</span><b>{{ ramText(product.ram_mb) }}</b></div>
              <div class="spec-item"><span>硬盘</span><b>{{ product.disk_gb }} GB</b></div>
              <div class="spec-item"><span>带宽</span><b>{{ product.bandwidth_mbps }} Mbps</b></div>
              <div class="spec-item"><span>IP 数量</span><b>{{ product.ip_count }} 个</b></div>
              <div class="spec-item"><span>网卡</span><b>{{ product.nic_count }} 个</b></div>
              <div class="spec-item"><span>计费模式</span><b>{{ product.billing_mode_label || '包月' }}</b></div>
              <div class="spec-item" v-if="product.billing_mode === 'transfer_quota'">
                <span>流量包</span><b>{{ product.transfer_quota_gb || '-' }} GB/月</b>
              </div>
            </template>
            <template v-else>
              <div class="spec-item"><span>带宽</span><b>{{ product.bandwidth_mbps }} Mbps</b></div>
              <div class="spec-item"><span>IP 数量</span><b>{{ product.ip_count }} 个</b></div>
              <div class="spec-item"><span>计费模式</span><b>{{ product.billing_mode_label || '包月' }}</b></div>
              <div class="spec-item" v-if="product.billing_mode === 'transfer_quota'">
                <span>流量包</span><b>{{ product.transfer_quota_gb || '-' }} GB/月</b>
              </div>
            </template>
          </div>

          <template v-if="product.category === 'edge'">
            <h3 class="blk-title">对接协议</h3>
            <div class="proto-row">
              <button
                type="button"
                class="proto-btn"
                :class="{ active: orderForm.accel_type === 'gre' }"
                @click="orderForm.accel_type = 'gre'"
              >GRE</button>
              <button
                type="button"
                class="proto-btn"
                :class="{ active: orderForm.accel_type === 'wireguard' }"
                @click="orderForm.accel_type = 'wireguard'"
              >WireGuard</button>
            </div>
          </template>

          <h3 class="blk-title">可用区域与网络</h3>
          <div class="spec-grid region-grid">
            <div class="spec-item"><span>区域</span><b>{{ product.region_name || '-' }}</b></div>
            <div class="spec-item"><span>国家</span><b>{{ product.country_name || '-' }}</b></div>
            <div class="spec-item"><span>城市</span><b>{{ product.city_name || '-' }}</b></div>
            <div class="spec-item"><span>可用区</span><b>{{ product.zone_name || product.availability_zone_name || '-' }}</b></div>
            <div class="spec-item"><span>IP 属性</span><b>{{ ipAttributeText }}</b></div>
            <div class="spec-item"><span>网络类型</span><b>{{ productNetworkTypeText }}</b></div>
            <div class="spec-item"><span>ASN 性质</span><b>{{ productAsnNatureText }}</b></div>
            <div v-if="product.ip_delivery_mode === 'nat'" class="spec-item">
              <span>IP 交付</span><b>NAT 交付</b>
            </div>
          </div>
          <el-alert
            v-if="product.ip_delivery_mode === 'nat'"
            type="warning"
            :closable="false"
            show-icon
            style="margin-top:12px"
            title="该产品为 NAT IP，无法公网直连"
          />

          <template v-if="product.category === 'vps'">
            <h3 class="blk-title">操作系统</h3>
            <div v-if="osOptions.length" class="os-cards">
              <button
                v-for="item in osOptions"
                :key="item.id"
                type="button"
                class="os-card"
                :class="{ active: orderForm.os_template_id === item.id }"
                @click="selectOs(item)"
              >
                <div class="os-card-name">{{ osLabel(item) }}</div>
              </button>
            </div>
            <el-empty v-else description="暂无可用系统版本" :image-size="64" />
          </template>

          <div v-if="sampleIps.length" class="sample-ip-box">
            <div class="sample-ip-title">示例 IP</div>
            <div class="sample-ip-list">
              <el-tag v-for="ip in sampleIps" :key="ip" size="large" effect="plain" type="success">{{ ip }}</el-tag>
            </div>
          </div>

          <!-- 4. 灵活配置 / 阶梯计价（滑块） -->
          <template v-if="sliderItems.length">
            <h3 class="blk-title">灵活配置</h3>

            <div v-for="item in sliderItems" :key="item.kind" class="slider-block">
              <div class="slider-head">
                <span class="slider-label">{{ item.label }}</span>
                <span class="slider-val">{{ item.format(customSpec[item.field]) }}</span>
              </div>
              <el-slider
                v-model="customSpec[item.field]"
                :min="item.min"
                :max="item.max"
                :step="item.step"
                :disabled="item.min >= item.max"
                show-stops
                @change="(v) => onSliderChange(item, v)"
              />
              <div class="slider-range">
                <span>{{ item.format(item.min) }}</span>
                <span>{{ item.format(item.max) }}</span>
              </div>
            </div>

            <div v-if="quoteResult?.price?.breakdown?.length" class="breakdown-box">
              <div class="breakdown-title">超出部分明细</div>
              <div v-for="(b, i) in quoteResult.price.breakdown" :key="i" class="breakdown-row">
                <span>{{ breakdownLabel(b.resource_kind) }} × {{ b.upgrade_qty }}</span>
                <span>+{{ money(b.monthly_delta, product.currency) }}/月</span>
              </div>
            </div>
          </template>
        </div>

        <!-- 下单侧栏：动态价格 + 库存 -->
        <aside class="order ce-card">
          <div class="price-label">月租</div>
          <div class="price">
            <span class="amount">{{ displayMonthly }}</span>
            <span class="unit">/ 月</span>
          </div>
          <div v-if="hasOverage" class="price-break">
            <span>基础 {{ money(quoteResult?.price?.base_monthly_price ?? product.monthly_price, product.currency) }}</span>
            <span class="over">超出 +{{ overageAmount }}</span>
          </div>
          <div class="price-sub" v-if="showReputationPrice">
            或 {{ quoteResult?.price?.reputation_price ?? product.reputation_price }} 信誉值 / 月
          </div>
          <div class="price-sub" v-if="Number(product.setup_price)">
            安装费 {{ money(product.setup_price, product.currency) }}（一次性）
          </div>

          <!-- 库存提示功能保留，现阶段暂不展示 -->
          <div v-if="false && auth.isLoggedIn && stockText" class="stock-box" :class="{ warn: isBackorder }">
            <el-icon><Box /></el-icon>
            <span>{{ stockText }}</span>
          </div>
          <div v-if="deliveryNotice" class="delivery-box" :class="{ backorder: isBackorder }">
            <el-icon><Clock /></el-icon>
            <span>{{ deliveryNotice }}</span>
          </div>

          <div class="spec-summary">
            <div class="sum-title">当前选配</div>
            <template v-if="product.category === 'vps'">
              <div>{{ customSpec.cpu_cores }}核 / {{ ramText(customSpec.ram_mb) }} / {{ customSpec.disk_gb }}G</div>
              <div>{{ customSpec.bandwidth_mbps }}Mbps · {{ customSpec.ip_count }} IP</div>
              <div v-if="selectedOsLabel">系统 {{ selectedOsLabel }}</div>
            </template>
            <template v-else>
              <div>{{ customSpec.bandwidth_mbps }}Mbps · {{ customSpec.ip_count }} IP</div>
              <div>对接 {{ accelTypeLabel }}</div>
            </template>
          </div>

          <el-button type="primary" size="large" class="full" :loading="quoting" @click="openOrder">
            <el-icon class="el-icon--left"><ShoppingCart /></el-icon> 立即下单
          </el-button>
          <p class="tip">
            {{ orderTipText }}
          </p>
        </aside>
      </div>
    </div>

    <el-dialog v-model="orderVisible" title="确认下单" width="640px">
      <div class="order-summary">
        <div class="os-row"><span>类别</span><b>{{ categoryLabel(product) }}</b></div>
        <div class="os-row"><span>区域</span><b>{{ regionText }}</b></div>
        <div class="os-row"><span>选配规格</span><b>{{ orderSpecText }}</b></div>
        <div v-if="product?.category === 'vps'" class="os-row"><span>操作系统</span><b>{{ selectedOsLabel || '请选择' }}</b></div>
        <div v-if="product?.category === 'vps'" class="os-row"><span>登录用户</span><b>root</b></div>
        <div v-if="product?.category === 'edge'" class="os-row"><span>对接协议</span><b>{{ accelTypeLabel }}</b></div>
        <div class="os-row"><span>数量</span><b>×{{ orderForm.quantity }}</b></div>
        <div class="os-row total"><span>合计应付</span><b>{{ orderPayableText }}</b></div>
        <div v-if="selectedPaymentMethod?.reputation" class="os-row">
          <span>信誉值余额</span>
          <b>{{ selectedPaymentMethod.balance }}{{ selectedPaymentMethod.available === false ? `（${selectedPaymentMethod.disabled_reason || '余额不足'}）` : '' }}</b>
        </div>
        <div v-if="product?.ip_delivery_mode === 'nat'" class="os-row">
          <span>IP 交付</span><b>NAT 交付（非公网直连）</b>
        </div>
      </div>
      <el-form label-position="top" style="margin-top:8px">
        <el-form-item v-if="product?.category === 'vps'" label="操作系统" required>
          <el-select
            v-model="orderForm.os_template_id"
            placeholder="选择 Cloud 镜像版本"
            filterable
            style="width:100%"
            @change="onOsTemplateChange"
          >
            <el-option
              v-for="item in osOptions"
              :key="item.id || item.label"
              :label="osLabel(item)"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <template v-if="product?.category === 'vps'">
          <el-form-item label="登录密码" required>
            <div class="pwd-row">
              <el-input v-model="orderForm.password" type="password" show-password placeholder="至少 8 位" />
              <el-button @click="generatePassword">生成</el-button>
            </div>
          </el-form-item>
          <el-form-item label="确认密码">
            <el-input v-model="orderForm.password_confirm" type="password" show-password placeholder="再次输入密码" />
          </el-form-item>
        </template>
        <el-form-item label="数量">
          <el-input-number v-model="orderForm.quantity" :min="1" :max="product?.category === 'edge' ? 1 : 20" />
          <span v-if="product?.category === 'edge'" class="qty-hint">公网对接需按每个对端分别提交</span>
        </el-form-item>
        <el-form-item label="需求备注">
          <el-input v-model="orderForm.requirements" type="textarea" :rows="2" placeholder="如部署用途、特殊要求等" />
        </el-form-item>
        <el-form-item label="支付方式" required>
          <div v-loading="paymentMethodsLoading" class="payment-methods">
            <el-radio-group v-model="selectedPaymentChannel" class="payment-radio-group">
              <el-radio
                v-for="method in onlinePaymentMethods"
                :key="method.channel_id"
                :label="method.channel_id"
                :disabled="method.available === false"
                border
                class="payment-radio"
              >
                {{ method.label || method.provider_label }}
                <el-tag v-if="method.reputation" size="small" :type="method.available === false ? 'info' : 'success'" effect="plain">
                  余额 {{ method.balance }}{{ method.needed ? ` / 需 ${method.needed}` : '' }}
                </el-tag>
                <el-tag v-if="method.sandbox" size="small" type="warning" effect="plain">沙箱</el-tag>
              </el-radio>
            </el-radio-group>
            <el-alert
              v-if="reputationMethod?.available === false"
              type="warning"
              :closable="false"
              show-icon
              :title="reputationMethod.disabled_reason || '信誉值余额不足，请选择其他支付方式或联系管理员。'"
              style="margin-top:8px"
            />
            <el-alert
              v-if="!paymentMethodsLoading && !selectablePaymentMethods.length"
              type="warning"
              :closable="false"
              show-icon
              title="当前没有可用支付方式。信誉值余额不足时请使用在线支付，或联系管理员充值。"
            />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="orderVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="paymentMethodsLoading || !selectablePaymentMethods.length"
          @click="submitOrder"
        >{{ submitOrderButtonText }}</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="qrPayVisible"
      title="扫码支付"
      width="380px"
      :close-on-click-modal="false"
      @closed="stopPaymentPolling"
    >
      <div class="qr-payment">
        <img v-if="qrCodeImage" :src="qrCodeImage" alt="支付二维码">
        <el-skeleton v-else :rows="4" animated />
        <p>{{ activePayment?.channel_name || '在线支付' }} · {{ activePayment?.currency }}{{ activePayment?.amount }}</p>
        <p class="qr-status">
          {{ paymentHintText }}
        </p>
      </div>
      <template #footer>
        <el-button @click="router.push({ name: 'orders' })">稍后在订单中查看</el-button>
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
  directCheckoutOrder,
  getBillPaymentMethods,
  getPaymentTransaction,
  getOsTemplates,
  getProduct,
  getProductDeliveryOptions,
  quoteProduct,
} from '@/api'
import { useAuthStore } from '@/store/auth'
import { launchCheckout } from '@/utils/checkout'
import { AIRWALLEX_ELEMENTS_SDK, loadLocalScript } from '@/utils/vendorAssets'
import {
  asnNatureLabel, ASN_NATURE_ORDER, BACKORDER_HINT, categoryLabel, IP_ATTR_ORDER, isHotSale, money,
  networkTypeLabel, ramText, sortByCode, sortNetworkTypes,
} from '@/utils/format'

const UPGRADE_DIVISOR = {
  cpu: 1, ram: 1024, disk: 1, bandwidth: 1, ip: 1, nic: 1,
}

const KIND_META = {
  cpu: {
    field: 'cpu_cores', label: 'CPU', step: 1,
    format: (v) => `${v} 核`,
    overText: (cur, base) => `${cur - base} 核`,
  },
  ram: {
    field: 'ram_mb', label: '内存', step: 1024,
    format: (v) => ramText(v),
    overText: (cur, base) => ramText(cur - base),
  },
  disk: {
    field: 'disk_gb', label: '硬盘', step: 10,
    format: (v) => `${v} GB`,
    overText: (cur, base) => `${cur - base} GB`,
  },
  bandwidth: {
    field: 'bandwidth_mbps', label: '带宽', step: 5,
    format: (v) => `${v} Mbps`,
    overText: (cur, base) => `${cur - base} Mbps`,
  },
  ip: {
    field: 'ip_count', label: 'IP 数量', step: 1,
    format: (v) => `${v} 个`,
    overText: (cur, base) => `${cur - base} 个`,
  },
  nic: {
    field: 'nic_count', label: '网卡', step: 1,
    format: (v) => `${v} 个`,
    overText: (cur, base) => `${cur - base} 个`,
  },
}

const BREAKDOWN_LABEL = {
  cpu: 'CPU', ram: '内存', disk: '硬盘', bandwidth: '带宽', ip: 'IP', nic: '网卡',
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const product = ref(null)
const loading = ref(false)
const quoting = ref(false)
const quoteResult = ref(null)
const deliveryOptions = ref(null)
const lastOrder = ref(null)
const orderVisible = ref(false)
const submitting = ref(false)
const orderForm = reactive({
  quantity: 1,
  requested_os: '',
  os_template_id: null,
  requirements: '',
  username: 'root',
  password: '',
  password_confirm: '',
  sshkeys: '',
  nameserver: '',
  accel_type: 'gre',
})
let lastDefaultUser = 'root'
const paymentMethodsLoading = ref(false)
const paymentMethods = ref([])
const selectedPaymentChannel = ref(null)
const qrPayVisible = ref(false)
const qrCodeImage = ref('')
const activePayment = ref(null)
const customSpec = reactive({
  cpu_cores: 1, ram_mb: 1024, disk_gb: 40, nic_count: 1, bandwidth_mbps: 5, ip_count: 1,
})
const osOptions = ref([])

function osLabel(item) {
  return item?.label || `${item?.name || ''} ${item?.version || ''}`.trim()
}

const selectedOs = computed(() => osOptions.value.find((row) => row.id === orderForm.os_template_id) || null)
const selectedOsLabel = computed(() => (selectedOs.value ? osLabel(selectedOs.value) : ''))

function applyDefaultUsername() {
  orderForm.username = 'root'
  lastDefaultUser = 'root'
}

function onOsTemplateChange(id) {
  const item = osOptions.value.find((row) => row.id === id)
  orderForm.requested_os = item ? osLabel(item) : ''
  applyDefaultUsername(item)
}

function selectOs(item) {
  orderForm.os_template_id = item?.id || null
  onOsTemplateChange(orderForm.os_template_id)
}

function generatePassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%'
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  let pwd = ''
  for (const byte of bytes) pwd += chars[byte % chars.length]
  orderForm.password = pwd
  orderForm.password_confirm = pwd
}

async function loadOsOptions(productData) {
  if (productData?.category !== 'vps') {
    osOptions.value = []
    return
  }
  try {
    const res = await getOsTemplates({ product_id: productData?.id })
    osOptions.value = res?.data || []
  } catch {
    osOptions.value = Array.isArray(productData?.os_templates) ? productData.os_templates : []
  }
  if (!orderForm.os_template_id && osOptions.value.length) {
    selectOs(osOptions.value[0])
    return
  }
  applyDefaultUsername()
}

let quoteTimer = null
let paymentPollingTimer = null

const productNetworkTypeText = computed(() => {
  const p = product.value
  if (!p) return '-'
  if (Array.isArray(p.network_types) && p.network_types.length) {
    return sortNetworkTypes(p.network_types).map((t) => t.label || t.name || networkTypeLabel(t.value || t.code)).join(' / ')
  }
  return p.network_type_label || networkTypeLabel(p.network_type)
})
const productAsnNatureText = computed(() => {
  const p = product.value
  if (!p) return '-'
  if (Array.isArray(p.asn_natures) && p.asn_natures.length) {
    return sortByCode(p.asn_natures, ASN_NATURE_ORDER).map((t) => t.label || asnNatureLabel(t.value)).join(' / ')
  }
  return p.asn_nature_label || asnNatureLabel(p.asn_nature)
})
const ipAttributeList = computed(() => {
  const raw = product.value?.ip_attribute_list || []
  const seen = new Set()
  const items = raw.filter((item) => {
    const key = String(item?.value ?? item?.label ?? '').trim().toLowerCase()
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
  return sortByCode(items, IP_ATTR_ORDER)
})
const ipAttributeText = computed(() =>
  ipAttributeList.value.map((item) => item.label).filter(Boolean).join(' / ') || '-')
const accelTypeLabel = computed(() =>
  orderForm.accel_type === 'wireguard' ? 'WireGuard' : 'GRE')
const sampleIps = computed(() =>
  String(product.value?.sample_ip || '')
    .split(/[,，\s]+/)
    .map((s) => s.trim())
    .filter(Boolean),
)
const isBackorder = computed(() => {
  if (deliveryOptions.value && Object.prototype.hasOwnProperty.call(deliveryOptions.value, 'is_backorder')) {
    return !!deliveryOptions.value.is_backorder
  }
  return !!product.value?.allow_backorder
})
const deliveryNotice = computed(() => (isBackorder.value ? BACKORDER_HINT : ''))
const orderTipText = computed(() => '确认规格并完成支付即可。开通在后台进行，完成后可在「我的服务」管理。')
const paymentHintText = computed(() => '支付完成后即可离开，系统将在后台开通。')
const onlinePaymentMethods = computed(() =>
  paymentMethods.value.filter((item) => item.online && item.channel_id))
const reputationMethod = computed(() =>
  onlinePaymentMethods.value.find((item) => item.reputation) || null)
const selectablePaymentMethods = computed(() =>
  onlinePaymentMethods.value.filter((item) => item.available !== false))
const submitOrderButtonText = computed(() => {
  if (submitting.value) {
    return isReputationPay.value ? '正在使用信誉值支付…' : '正在连接支付通道…'
  }
  return isReputationPay.value ? '确认并用信誉值支付' : '确认并支付'
})

const baseSpec = computed(() => {
  const p = product.value
  if (!p) return {}
  const t = p.template_spec || {}
  return {
    cpu_cores: t.cpu_cores ?? p.cpu_cores ?? 0,
    ram_mb: t.ram_mb ?? p.ram_mb ?? 0,
    disk_gb: t.disk_gb ?? p.disk_gb ?? 0,
    nic_count: t.nic_count ?? p.nic_count ?? 0,
    bandwidth_mbps: t.bandwidth_mbps ?? p.bandwidth_mbps ?? 0,
    ip_count: t.ip_count ?? p.ip_count ?? 0,
  }
})

const activeRules = computed(() =>
  (product.value?.upgrade_rules || []).filter((r) => r.is_active !== false))

const sliderItems = computed(() => {
  const p = product.value
  if (!p) return []
  const kinds = [...new Set(activeRules.value.map((r) => r.resource_kind))]
  if (!kinds.length) return []

  const isEdge = p.category === 'edge'
  const base = baseSpec.value
  return kinds
    .filter((k) => KIND_META[k])
    .filter((k) => !isEdge || k === 'bandwidth' || k === 'ip')
    .map((kind) => {
      const meta = KIND_META[kind]
      const baseVal = base[meta.field] ?? 0
      const range = calcTierSliderRange(kind, baseVal, activeRules.value)
      return {
        kind,
        ...meta,
        baseVal,
        min: range.min,
        max: Math.max(range.min, range.max),
      }
    })
    .sort((a, b) => Object.keys(KIND_META).indexOf(a.kind) - Object.keys(KIND_META).indexOf(b.kind))
})

/** 从阶梯规则推导滑块区间：起始为基准规格，上限为规则 max_qty（绝对值，不含基准叠加） */
function calcTierSliderRange(kind, baseVal, rules) {
  const kindRules = rules.filter((r) => r.resource_kind === kind)
  const div = UPGRADE_DIVISOR[kind] || 1
  if (!kindRules.length) {
    return { min: baseVal, max: baseVal }
  }

  let tierMaxQty = 0
  let hasMax = false

  for (const r of kindRules) {
    if (r.max_qty != null && r.max_qty !== '') {
      hasMax = true
      tierMaxQty = Math.max(tierMaxQty, Number(r.max_qty))
    }
  }

  if (!hasMax) {
    const maxLo = Math.max(...kindRules.map((r) => Number(r.min_qty ?? 0)))
    const minLo = Math.min(...kindRules.map((r) => Number(r.min_qty ?? 0)))
    tierMaxQty = Math.max(maxLo + 20, minLo + 10)
  }

  const minSpec = baseVal
  const maxSpec = tierMaxQty * div

  return { min: minSpec, max: Math.max(minSpec, maxSpec) }
}

function snapRamMb(v) {
  return Math.max(1024, Math.round(Number(v) / 1024) * 1024)
}

function clampSpecToSliders() {
  const isEdge = product.value?.category === 'edge'
  for (const item of sliderItems.value) {
    let v = customSpec[item.field]
    if (item.kind === 'ram' && !isEdge) v = snapRamMb(v)
    customSpec[item.field] = Math.min(item.max, Math.max(item.min, v))
  }
}

function initCustomSpec() {
  const p = product.value
  if (!p) return
  const isEdge = p.category === 'edge'
  Object.assign(customSpec, {
    cpu_cores: isEdge ? 0 : (p.cpu_cores ?? 1),
    ram_mb: isEdge ? 0 : snapRamMb(p.ram_mb ?? 1024),
    disk_gb: isEdge ? 0 : (p.disk_gb ?? 40),
    nic_count: isEdge ? 0 : (p.nic_count ?? 1),
    bandwidth_mbps: p.bandwidth_mbps ?? 5,
    ip_count: p.ip_count ?? 1,
  })
  clampSpecToSliders()
}

function onSliderChange(item, val) {
  let v = val
  if (item.kind === 'ram') v = snapRamMb(v)
  customSpec[item.field] = Math.min(item.max, Math.max(item.min, v))
  onSpecChange()
}

const displayMonthly = computed(() => {
  const price = quoteResult.value?.price
  const cur = price?.monthly_price ?? product.value?.monthly_price
  return money(cur, product.value?.currency)
})
const orderMonthlyTotalValue = computed(() => {
  const price = quoteResult.value?.price?.monthly_price ?? product.value?.monthly_price ?? 0
  return Number(price) * Number(orderForm.quantity || 1)
})
const orderSetupTotalValue = computed(() => {
  const setup = quoteResult.value?.price?.setup_price ?? product.value?.setup_price ?? 0
  return Number(setup) * Number(orderForm.quantity || 1)
})
const orderFirstPayment = computed(() =>
  money(orderMonthlyTotalValue.value + orderSetupTotalValue.value, product.value?.currency))
const selectedPaymentMethod = computed(() =>
  onlinePaymentMethods.value.find((item) => String(item.channel_id) === String(selectedPaymentChannel.value)))
const isReputationPay = computed(() => selectedPaymentMethod.value?.reputation || selectedPaymentChannel.value === 'reputation')
const showReputationPrice = computed(() => {
  const price = quoteResult.value?.price?.reputation_price ?? product.value?.reputation_price
  return Boolean(product.value?.reputation_visible && Number(price))
})
const orderPayableText = computed(() => {
  if (isReputationPay.value) {
    const needed = selectedPaymentMethod.value?.needed
      || quoteResult.value?.price?.reputation_price
      || product.value?.reputation_price
    return `${needed} 信誉值`
  }
  return orderFirstPayment.value
})

const hasOverage = computed(() => {
  const p = quoteResult.value?.price
  if (!p) return false
  return Number(p.monthly_price) > Number(p.base_monthly_price)
})

const overageAmount = computed(() => {
  const p = quoteResult.value?.price
  if (!p) return money(0)
  const diff = Number(p.monthly_price) - Number(p.base_monthly_price)
  return money(diff, p.currency)
})

const stockText = computed(() => {
  const stock = quoteResult.value?.stock
  if (!stock || stock.stock == null) return ''
  return `当前节点预计还可开通 ${stock.stock} 套该配置`
})

const regionText = computed(() => {
  const p = product.value
  if (!p) return '-'
  return [p.region_name, p.country_name, p.city_name].filter(Boolean).join(' · ') || '-'
})
const isHot = computed(() => isHotSale(product.value))

const orderSpecText = computed(() => {
  if (product.value?.category === 'vps') {
    return `${customSpec.cpu_cores}核/${ramText(customSpec.ram_mb)}/${customSpec.disk_gb}G/${customSpec.bandwidth_mbps}M/${customSpec.ip_count}IP`
  }
  return `${customSpec.bandwidth_mbps}Mbps · ${customSpec.ip_count} IP`
})

function breakdownLabel(kind) {
  return BREAKDOWN_LABEL[kind] || kind
}

function buildQuotePayload() {
  const payload = {
    bandwidth_mbps: customSpec.bandwidth_mbps,
    ip_count: customSpec.ip_count,
  }
  if (product.value?.category !== 'edge') {
    payload.cpu_cores = customSpec.cpu_cores
    payload.ram_mb = customSpec.ram_mb
    payload.disk_gb = customSpec.disk_gb
    payload.nic_count = customSpec.nic_count
  }
  return payload
}

async function fetchQuote() {
  if (!product.value) return
  quoting.value = true
  try {
    quoteResult.value = await quoteProduct(product.value.id, buildQuotePayload())
  } catch (e) {
    /* 拦截器提示 */
  } finally {
    quoting.value = false
  }
}

function onSpecChange() {
  clearTimeout(quoteTimer)
  quoteTimer = setTimeout(fetchQuote, 350)
}

async function openOrder() {
  if (!auth.isLoggedIn) {
    ElMessage.warning('请先登录后再下单')
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  if (product.value?.category === 'vps') {
    if (!orderForm.os_template_id && osOptions.value.length) selectOs(osOptions.value[0])
    if (!orderForm.password) generatePassword()
  }
  orderVisible.value = true
  await loadPaymentMethods()
}

async function loadPaymentMethods() {
  if (!product.value) return
  paymentMethodsLoading.value = true
  paymentMethods.value = []
  selectedPaymentChannel.value = null
  try {
    const res = await getBillPaymentMethods({
      currency: product.value.currency,
      product_id: product.value.id,
      quantity: orderForm.quantity,
      ...buildQuotePayload(),
    })
    paymentMethods.value = res?.data || []
    const preferred = selectablePaymentMethods.value.find((item) => item.reputation)
      || selectablePaymentMethods.value[0]
      || onlinePaymentMethods.value[0]
    selectedPaymentChannel.value = preferred?.channel_id || null
  } catch {
    paymentMethods.value = []
  } finally {
    paymentMethodsLoading.value = false
  }
}

async function launchAirwallex(checkout) {
  const payload = checkout.sdk_payload || {}
  await loadLocalScript(AIRWALLEX_ELEMENTS_SDK)
  const sdk = window.AirwallexComponentsSDK
  if (!sdk?.init) throw new Error('Airwallex 收银台未正确加载')
  const { payments } = await sdk.init({
    env: payload.env,
    enabledElements: ['payments'],
  })
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
    activePayment.value = payment
    if (payment.status === 'succeeded') {
      stopPaymentPolling()
      qrPayVisible.value = false
      ElMessage.success(paidSuccessMessage())
      router.push({ name: 'services', query: { paid: '1' } })
    } else if (['failed', 'cancelled', 'expired'].includes(payment.status)) {
      stopPaymentPolling()
      ElMessage.error(payment.failure_reason || '支付未成功，请重新发起支付')
    }
  } catch {
    // 短暂网络错误不关闭二维码，下一轮继续查询。
  }
}

async function handleCheckout(checkout, transaction) {
  if (!checkout) {
    router.push({ name: 'services', query: { paid: '1' } })
    return
  }
  activePayment.value = transaction || null
  await launchCheckout(checkout, {
    onQr: async (payload) => {
      qrCodeImage.value = payload.qr_code_url || await QRCode.toDataURL(payload.qr_code_text, {
        width: 240,
        margin: 1,
        errorCorrectionLevel: 'M',
      })
      qrPayVisible.value = true
      startPaymentPolling()
    },
    onSdk: async (payload) => {
      if (payload.sdk === 'airwallex') {
        await launchAirwallex(payload)
        return
      }
      ElMessage.info('请按支付渠道提示完成支付')
      router.push({ name: 'services', query: { paid: '1' } })
    },
  })
}

async function submitOrder() {
  if (!selectedPaymentChannel.value) {
    ElMessage.warning('请选择支付方式')
    return
  }
  if (selectedPaymentMethod.value?.available === false) {
    ElMessage.warning(selectedPaymentMethod.value.disabled_reason || '当前支付方式不可用')
    return
  }
  if (product.value?.category === 'vps') {
    if (!orderForm.os_template_id) {
      ElMessage.warning('请选择操作系统')
      return
    }
    if (!orderForm.password) generatePassword()
    if (orderForm.password !== orderForm.password_confirm) {
      ElMessage.warning('两次密码不一致')
      return
    }
    if (orderForm.password.length < 8) {
      ElMessage.warning('密码至少 8 位')
      return
    }
  }
  submitting.value = true
  try {
    const payload = {
      product_id: product.value.id,
      quantity: orderForm.quantity,
      requested_os: orderForm.requested_os,
      os_template_id: orderForm.os_template_id || undefined,
      username: product.value?.category === 'vps' ? 'root' : undefined,
      password: orderForm.password || undefined,
      sshkeys: orderForm.sshkeys || undefined,
      nameserver: orderForm.nameserver || undefined,
      requirements: orderForm.requirements,
      source_url: window.location.href,
      ...buildQuotePayload(),
    }
    if (product.value?.category === 'edge') {
      payload.accel_type = orderForm.accel_type
      const protoLine = `对接协议：${accelTypeLabel.value}`
      payload.requirements = [protoLine, orderForm.requirements].filter(Boolean).join('\n')
    }
    if (isReputationPay.value) {
      payload.payment_method = 'reputation'
    } else {
      payload.channel_id = selectedPaymentChannel.value
    }
    const res = await directCheckoutOrder(payload)
    const result = res?.data || {}
    lastOrder.value = result.order || null
    orderVisible.value = false
    if (result.provision_result || result.provision_queued || isReputationPay.value) {
      ElMessage.success(paidSuccessMessage(
        isReputationPay.value ? '信誉值支付成功，系统正在后台开通' : '订单已确认，系统正在后台开通',
      ))
      router.push({ name: 'services', query: { paid: '1' } })
      return
    }
    if (!result.checkout) {
      ElMessage.warning('订单已创建，但未返回支付页面，请前往账单继续支付')
      router.push({ name: 'bills' })
      return
    }
    ElMessage.success('正在打开支付页面')
    await handleCheckout(result.checkout, result.transaction)
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.response?.data?.detail || error?.message || '创建订单或支付失败')
  } finally {
    submitting.value = false
  }
}

function paidSuccessMessage(fallback = '支付成功，系统正在后台开通。完成后可在「我的服务」中管理') {
  return fallback
}

async function loadDeliveryOptions() {
  if (!product.value?.id) return
  try {
    deliveryOptions.value = await getProductDeliveryOptions(product.value.id)
  } catch {
    deliveryOptions.value = null
  }
}

watch(() => auth.isLoggedIn, () => {
  fetchQuote()
  loadDeliveryOptions()
})

watch(
  () => orderForm.quantity,
  () => {
    if (orderVisible.value) loadPaymentMethods()
  },
)

onMounted(async () => {
  loading.value = true
  try {
    const res = await getProduct(route.params.id)
    product.value = res
    initCustomSpec()
    await Promise.all([fetchQuote(), loadDeliveryOptions(), loadOsOptions(res)])
  } catch (e) {
    ElMessage.error('产品不存在或已下线')
    router.push('/products')
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(stopPaymentPolling)
</script>

<style scoped>
.detail-page {
  min-height: 70vh;
  padding: 20px 0 48px;
}
.bread {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ce-muted);
  font-size: 14px;
  margin-bottom: 20px;
}
.bread a:hover {
  color: var(--ce-primary);
}
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 16px;
  align-items: start;
}
.main {
  padding: 22px;
}
.main-head {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.main-head h1 {
  font-size: 22px;
  margin: 0;
}
.hot-badge {
  font-size: 13px;
  font-weight: 700;
  color: #e11d48;
}
.head-loc {
  margin-left: auto;
  font-size: 13px;
  color: var(--ce-muted);
}
.blk-title {
  font-size: 15px;
  margin: 22px 0 12px;
  padding-left: 10px;
  border-left: 3px solid var(--ce-primary);
}
.blk-hint {
  color: var(--ce-muted);
  font-size: 13px;
  margin: -6px 0 18px;
  line-height: 1.6;
}
.spec-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.region-grid {
  grid-template-columns: repeat(3, 1fr);
}
.spec-item {
  background: var(--ce-surface-subtle);
  border: 1px solid var(--ce-border);
  border-radius: var(--ce-radius-sm);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.spec-item span {
  font-size: 12px;
  color: var(--ce-muted);
}
.spec-item b {
  font-size: 16px;
}
.ip-attr-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.slider-block {
  background: var(--ce-surface-subtle);
  border: 1px solid var(--ce-border);
  border-radius: var(--ce-radius-sm);
  padding: 18px 20px;
  margin-bottom: 14px;
}
.slider-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.slider-label {
  font-weight: 700;
  font-size: 15px;
}
.slider-val {
  font-size: 16px;
  font-weight: 800;
  color: var(--ce-primary);
}
.slider-range {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--ce-muted);
  margin-top: 4px;
}
.breakdown-box {
  margin-top: 16px;
  padding: 14px 16px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 12px;
}
.breakdown-title {
  font-size: 13px;
  font-weight: 700;
  color: #92400e;
  margin-bottom: 8px;
}
.breakdown-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #78350f;
  padding: 4px 0;
}
.order {
  padding: 20px;
  position: sticky;
  top: 68px;
}
.price-label {
  font-size: 13px;
  color: var(--ce-muted);
  margin-bottom: 4px;
}
.price .amount {
  font-size: 32px;
  font-weight: 850;
  color: var(--ce-price);
}
.price .unit {
  color: var(--ce-muted);
  margin-left: 4px;
}
.price-break {
  display: flex;
  gap: 10px;
  font-size: 13px;
  color: var(--ce-muted);
  margin-top: 6px;
}
.price-break .over {
  color: #d97706;
  font-weight: 600;
}
.price-sub {
  color: var(--ce-muted);
  font-size: 13px;
  margin-top: 6px;
}
.sample-ip-box {
  margin-top: 16px;
  padding: 14px 16px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
}
.sample-ip-title {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
  margin-bottom: 8px;
}
.sample-ip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.stock-box {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 12px 14px;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 10px;
  color: #047857;
  font-size: 13px;
  font-weight: 600;
}
.stock-box.warn {
  background: #fffbeb;
  border-color: #fde68a;
  color: #b45309;
}
.delivery-box {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 12px 14px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  color: #1d4ed8;
  font-size: 13px;
  font-weight: 600;
}
.delivery-box.backorder {
  background: #fff7ed;
  border-color: #fdba74;
  color: #c2410c;
}
.spec-summary {
  margin-top: 16px;
  padding: 12px 14px;
  background: var(--ce-surface-subtle);
  border: 1px solid var(--ce-border);
  border-radius: var(--ce-radius-sm);
  font-size: 13px;
  line-height: 1.7;
  color: #374151;
}
.sum-title {
  font-weight: 700;
  margin-bottom: 4px;
  color: var(--ce-text);
}
.includes {
  list-style: none;
  padding: 0;
  margin: 22px 0;
}
.includes li {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  color: #374151;
}
.full {
  width: 100%;
  margin-top: 16px;
}
.tip {
  font-size: 12px;
  color: var(--ce-muted);
  text-align: center;
  margin: 12px 0 0;
}
.os-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 8px;
}
.os-card {
  text-align: left;
  padding: 14px 16px;
  border: 1px solid var(--ce-border);
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
}
.os-card.active {
  border-color: var(--ce-primary);
  box-shadow: 0 0 0 1px var(--ce-primary);
}
.os-card-name {
  font-weight: 700;
}
.proto-row {
  display: flex;
  gap: 10px;
}
.proto-btn {
  min-width: 120px;
  padding: 10px 16px;
  border: 1px solid var(--ce-border);
  border-radius: 8px;
  background: #fff;
  font-weight: 700;
  cursor: pointer;
}
.proto-btn.active {
  border-color: var(--ce-primary);
  box-shadow: 0 0 0 1px var(--ce-primary);
  color: var(--ce-primary);
}
.pwd-row {
  display: flex;
  gap: 8px;
  width: 100%;
}
.pwd-row .el-input {
  flex: 1;
}
.order-summary {
  background: var(--ce-surface-subtle);
  border: 1px solid var(--ce-border);
  border-radius: var(--ce-radius-sm);
  padding: 14px 16px;
}
.os-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 14px;
  gap: 12px;
}
.os-row span {
  color: var(--ce-muted);
  flex-shrink: 0;
}
.os-row b {
  text-align: right;
}
.qty-hint {
  margin-left: 10px;
  color: var(--ce-muted);
  font-size: 12px;
}
.payment-methods {
  width: 100%;
  min-height: 36px;
}
.payment-radio-group {
  display: flex;
  width: 100%;
  flex-wrap: wrap;
  gap: 8px;
}
.payment-radio {
  margin: 0;
  min-width: 150px;
  height: auto;
  padding: 9px 12px;
}
.payment-radio :deep(.el-tag) {
  margin-left: 6px;
}
.qr-payment {
  display: flex;
  align-items: center;
  flex-direction: column;
  text-align: center;
  color: var(--ce-muted);
}
.qr-payment img {
  width: 240px;
  height: 240px;
  margin: 6px 0 12px;
}
.qr-payment p {
  margin: 4px 0;
}
.qr-payment .qr-status {
  font-size: 13px;
}
@media (max-width: 860px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
  .order {
    position: static;
  }
  .spec-grid,
  .region-grid {
    grid-template-columns: 1fr 1fr;
  }
  .qr-payment img {
    width: min(240px, 70vw);
    height: auto;
  }
}
@media (max-width: 560px) {
  .spec-grid,
  .region-grid {
    grid-template-columns: 1fr;
  }
}
</style>
