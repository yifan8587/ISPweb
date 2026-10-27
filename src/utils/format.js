export function mbToGb(mb) {
  const n = Number(mb)
  if (!Number.isFinite(n) || n <= 0) return 0
  const gb = Math.round((n / 1024) * 100) / 100
  return Number.isInteger(gb) ? gb : gb
}

export function gbToMb(gb) {
  const n = Number(gb)
  if (!Number.isFinite(n) || n <= 0) return 0
  return Math.round(n * 1024)
}

export function ramText(mb) {
  const gb = mbToGb(mb)
  return gb ? `${gb} GB` : '0 GB'
}

export function money(v, currency = 'USD') {
  const code = String(currency || 'USD').toUpperCase()
  const sym = { CNY: '¥', USD: '$', CREDIT: '' }[code] || ''
  const suffix = code === 'CREDIT' ? ' 信誉' : ''
  const n = Number(v || 0)
  return `${sym}${n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${suffix}`
}

export const networkTypeLabel = (v) => ({ home_broadband: '家宽', idc: 'IDC' }[v] || v || '-')
export const asnNatureLabel = (v) => ({ isp: '单ISP', non_isp: '非ISP', dual_isp: '双ISP' }[v] || v || '-')
export const ipAttrLabel = (v) => ({ native: '原生', broadcast: '广播' }[v] || v || '-')

/** 网络类型 / IP 线路展示顺序：不限 → IDC → 家宽 */
export const NETWORK_TYPE_ORDER = ['idc', 'home_broadband']
export const IP_ATTR_ORDER = ['broadcast', 'native']
export const ASN_NATURE_ORDER = ['non_isp', 'isp', 'dual_isp']

export function sortByCode(list = [], order = []) {
  const rank = Object.fromEntries(order.map((code, i) => [code, i]))
  return [...list].sort((a, b) => {
    const av = String(a?.value || a?.code || a || '')
    const bv = String(b?.value || b?.code || b || '')
    return (rank[av] ?? 50) - (rank[bv] ?? 50)
  })
}

export function sortNetworkTypes(list = []) {
  const rank = Object.fromEntries(NETWORK_TYPE_ORDER.map((code, i) => [code, i]))
  return [...list].sort((a, b) => {
    const av = String(a?.value || a?.code || a || '')
    const bv = String(b?.value || b?.code || b || '')
    return (rank[av] ?? 50) - (rank[bv] ?? 50)
  })
}

export function categoryLabel(productOrCategory) {
  const cat = typeof productOrCategory === 'string'
    ? productOrCategory
    : productOrCategory?.category
  if (cat === 'edge') return '公网对接'
  if (cat === 'vps') return 'VPS'
  if (typeof productOrCategory === 'object' && productOrCategory?.category_label) {
    return productOrCategory.category_label
  }
  return cat || '-'
}

export function isNatDelivery(product) {
  return product?.ip_delivery_mode === 'nat'
}

export function isHotSale(product) {
  return Boolean(product?.hot_sale || product?.is_hot_sale)
}

export function sellerLabel(product) {
  const name = String(product?.supplier_info?.name || product?.supplier_name || '').trim()
  return name || '自营'
}

export function productLocationText(product) {
  const p = product || {}
  const zone = p.zone_name || p.availability_zone_name
  return [p.country_name, p.city_name, zone].filter(Boolean).join(' · ') || '全球'
}

const ACCEL_LABELS = { gre: 'GRE', wireguard: 'WireGuard' }

export function parseAccelTypes(v) {
  const items = Array.isArray(v) ? v : String(v || '').split(/[,;/]/)
  const out = []
  for (const item of items) {
    let value = String(item || '').trim().toLowerCase()
    if (value === 'wg') value = 'wireguard'
    if ((value === 'gre' || value === 'wireguard') && !out.includes(value)) out.push(value)
  }
  return out
}

export const accelLabel = (v) => {
  const types = parseAccelTypes(v)
  return types.length ? types.map((t) => ACCEL_LABELS[t]).join(' / ') : '-'
}

export const BACKORDER_HINT = '库存紧张，交付稍有延迟'

export const vpsStatusTag = {
  running: { label: '运行中', type: 'success' },
  stopped: { label: '已停止', type: 'info' },
  suspended: { label: '已暂停', type: 'warning' },
  creating: { label: '创建中', type: 'primary' },
  deleting: { label: '删除中', type: 'danger' },
  error: { label: '故障', type: 'danger' },
}

export const instanceStatusTag = {
  provisioning: { label: '开通中', type: 'primary' },
  active: { label: '运行中', type: 'success' },
  suspended: { label: '已暂停', type: 'warning' },
  terminated: { label: '已终止', type: 'info' },
  expired: { label: '已过期', type: 'info' },
  error: { label: '故障', type: 'danger' },
}

export const orderStatusTag = {
  draft: { label: '草稿', type: 'info' },
  pending: { label: '待审批', type: 'warning' },
  approved: { label: '已审批', type: 'primary' },
  provisioning: { label: '开通中', type: 'primary' },
  active: { label: '服务中', type: 'success' },
  suspend_pending: { label: '待暂停', type: 'warning' },
  suspended: { label: '已暂停', type: 'warning' },
  terminate_pending: { label: '待终止', type: 'warning' },
  terminated: { label: '已终止', type: 'info' },
  rejected: { label: '已驳回', type: 'danger' },
}

export const billStatusTag = {
  unpaid: { label: '待支付', type: 'warning' },
  paid: { label: '已支付', type: 'success' },
  overdue: { label: '逾期', type: 'danger' },
  cancelled: { label: '已取消', type: 'info' },
  refunding: { label: '退款中', type: 'warning' },
  refunded: { label: '已退款', type: 'info' },
}

export const paymentMethodLabel = {
  cash: '现金',
  bank_transfer: '银行转账',
  wechat: '微信支付',
  alipay: '支付宝',
  paypal: 'PayPal',
  stripe: 'Stripe',
  airwallex: 'Airwallex',
  unionpay: '银联在线支付',
  credit_payment: '信用支付',
  other: '其他',
}

export const serviceTypeLabel = {
  vps: 'VPS',
  edge: '公网对接',
  ip: 'IP 地址',
  bandwidth: '带宽',
}

export function curSym(currency = 'USD') {
  return { CNY: '¥', USD: '$', CREDIT: '' }[String(currency || 'USD').toUpperCase()] || ''
}

export function formatProvisionHours(hours) {
  const n = Number(hours)
  if (!n || n <= 0) return ''
  if (n < 24) return `约 ${n} 小时`
  const days = Math.floor(n / 24)
  const rem = n % 24
  return rem ? `约 ${days} 天 ${rem} 小时` : `约 ${days} 天`
}

export function formatDate(v, withTime = false) {
  if (!v) return '-'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return v
  const p = (n) => String(n).padStart(2, '0')
  const base = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
  return withTime ? `${base} ${p(d.getHours())}:${p(d.getMinutes())}` : base
}
