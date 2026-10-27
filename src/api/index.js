import request from './request'

// ── 认证 ──────────────────────────────────────────────────────
export const login = (data) => request.post('/auth/token/', data)
export const refreshToken = (data) => request.post('/auth/token/refresh/', data)
export const getMe = () => request.get('/auth/me/')
export const changePassword = (data) => request.post('/auth/me/change_password/', data)
export const register = (data) => request.post('/portal/register/', data)

// ── 公共：产品 / 地区 ───────────────────────────────────────────
export const getProducts = (params) => request.get('/portal/products/', { params })
export const getProduct = (id) => request.get(`/portal/products/${id}/`)
export const quoteProduct = (id, data) => request.post(`/portal/products/${id}/quote/`, data)
export const getProductDeliveryOptions = (id) => request.get(`/portal/products/${id}/delivery-options/`)
export const getLocations = () => request.get('/portal/locations/')
export const getSupportConfig = () => request.get('/portal/support-config/')
export const createSupportInquiry = (data) => request.post('/portal/support-inquiries/', data)

// ── 客户控制台 ──────────────────────────────────────────────────
export const getDashboard = () => request.get('/portal/dashboard/')
export const getProfile = () => request.get('/portal/profile/')
export const updateProfile = (data) => request.patch('/portal/profile/', data)

export const getServices = (params) => request.get('/portal/services/', { params })
export const quoteServiceChange = (id, data) => request.post(`/portal/services/${id}/change_quote/`, data)
export const requestServiceChange = (id, data) =>
  request.post(`/portal/services/${id}/change_request/`, data, { timeout: 60000 })
export const quoteServiceRenew = (id, data) => request.post(`/portal/services/${id}/renew_quote/`, data)
export const renewService = (id, data) =>
  request.post(`/portal/services/${id}/renew/`, data, { timeout: 60000 })
export const quoteTrialConvert = (id, data) => request.post(`/portal/services/${id}/convert_quote/`, data)
export const convertTrialService = (id, data) =>
  request.post(`/portal/services/${id}/convert/`, data, { timeout: 60000 })

export const getOrders = (params) => request.get('/portal/orders/', { params })
export const getOrder = (id) => request.get(`/portal/orders/${id}/`)
export const createOrder = (data) => request.post('/portal/orders/', data)
export const directCheckoutOrder = (data) =>
  request.post('/portal/orders/direct-checkout/', data, { timeout: 60000 })
export const getInquiries = (params) => request.get('/portal/inquiries/', { params })
export const getTickets = (params) => request.get('/portal/tickets/', { params })
export const createTicket = (data) => request.post('/portal/tickets/', data)
export const replyTicket = (id, data) => request.post(`/portal/tickets/${id}/reply/`, data)

export const getBills = (params) => request.get('/portal/bills/', { params })
export const getBill = (id) => request.get(`/portal/bills/${id}/`)
export const getBillPaymentMethods = (params) => request.get('/portal/bills/payment-methods/', { params })
export const getWallet = (params) => request.get('/portal/bills/wallet/', { params })
export const createRechargeBill = (data) => request.post('/portal/bills/recharge/', data)
export const payBillWithBalance = (id) => request.post(`/portal/bills/${id}/pay-with-balance/`)
export const payBill = (id, data) =>
  request.post(`/portal/bills/${id}/pay/`, data, { timeout: 60000 })
export const getPaymentTransaction = (transactionNo) =>
  request.get(`/customer/payment-transactions/${transactionNo}/`)

export const getMyVPS = (params) => request.get('/portal/vps/', { params })
export const getMyVPSDetail = (id) => request.get(`/portal/vps/${id}/`)
export const vpsPower = (id, action) => request.post(`/portal/vps/${id}/power/`, { action }, { timeout: 0 })
export const getVPSVncTicket = (id) => request.get(`/portal/vps/${id}/vnc_ticket/`, { timeout: 0 })

// 与 ISPmanager 资源管理控制台相同：浏览器只连本站 /ws/resource/vnc/<id>/。
// 生产环境再包进 URL 混淆。票据留在管理端，由管理端去连节点。
export async function portalVncWebSocketURL(id, { grant, ticket, port } = {}) {
  const token = localStorage.getItem('ispweb_access') || ''
  if (!token) return ''
  const params = { token }
  if (grant) params.grant = grant
  else if (ticket && port != null && port !== '') {
    params.vncticket = ticket
    params.port = port
  } else {
    return ''
  }
  const { canonicalQuery, guardWebSocket } = await import('@/utils/urlguard')
  const path = `/ws/resource/vnc/${id}/`
  const query = canonicalQuery(null, params)
  const guarded = await guardWebSocket(path, query)
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  if (guarded) return `${proto}//${window.location.host}${guarded}`
  return `${proto}//${window.location.host}${path}?${query}`
}
export const setVPSRootPassword = (id, payload) => {
  const data = typeof payload === 'string' ? { password: payload } : (payload || {})
  return request.post(`/portal/vps/${id}/set_root_password/`, data)
}
export const syncVPSNow = (id) => request.post(`/portal/vps/${id}/sync_now/`, {}, { timeout: 0 })
export const getVPSTraffic = (id, params = {}) => request.get(`/portal/vps/${id}/traffic/`, { params })
export const getOsImages = () => request.get('/portal/os-images/')
export const getOsTemplates = (params) => request.get('/portal/os-templates/', { params })
export const reinstallVPS = (id, data) => request.post(`/portal/vps/${id}/reinstall/`, data, { timeout: 0 })
export const getVPSSnapshots = (id) => request.get(`/portal/vps/${id}/snapshots/`)
export const createVPSSnapshot = (id, data) => request.post(`/portal/vps/${id}/snapshots/create/`, data)
export const restoreVPSSnapshot = (id, snapshotId) => request.post(`/portal/vps/${id}/snapshots/${snapshotId}/restore/`)
export const deleteVPSSnapshot = (id, snapshotId) => request.post(`/portal/vps/${id}/snapshots/${snapshotId}/delete/`)
export const getVPSSelfServiceJobs = (id) => request.get(`/portal/vps/${id}/self-service-jobs/`)

export const getMyEdge = (params) => request.get('/portal/edge/', { params })
export const getMyEdgeDetail = (id) => request.get(`/portal/edge/${id}/`)
export const getEdgeProtocolConfig = (id) => request.get(`/portal/edge/${id}/protocol_config/`)
export const updateEdgeProtocolConfig = (id, data) => request.patch(
  `/portal/edge/${id}/protocol_config/`,
  data,
  { timeout: 60000 },
)
export const pushEdgeToNode = (id, dryRun = false) => request.post(`/portal/edge/${id}/push_to_node/`, { dry_run: dryRun }, { timeout: 0 })
export const edgeWgGenkey = (id) => request.post(`/portal/edge/${id}/wg_genkey/`, {})
export const getEdgeTraffic = (id, params = {}) => request.get(`/portal/edge/${id}/traffic/`, { params })
export const getEdgeQuality = (id, params = {}) => request.get(`/portal/edge/${id}/quality/`, { params })
