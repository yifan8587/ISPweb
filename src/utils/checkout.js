function checkoutRedirectUrl(checkout) {
  return checkout?.url || checkout?.redirect_url || ''
}

export function submitGatewayForm(checkout) {
  const form = document.createElement('form')
  form.method = checkout.form_method || 'POST'
  form.action = checkout.form_action
  form.target = '_blank'
  form.style.display = 'none'
  Object.entries(checkout.form_fields || {}).forEach(([name, value]) => {
    const input = document.createElement('input')
    input.type = 'hidden'
    input.name = name
    input.value = String(value)
    form.appendChild(input)
  })
  document.body.appendChild(form)
  form.submit()
  form.remove()
}

export function openCheckoutWindow(url) {
  if (!url) return false
  // 不要把 noopener 放进 windowFeatures：部分浏览器会因此返回 null，
  // 被误判为弹窗拦截后又执行 location.assign，导致当前页也被跳走。
  const win = window.open(url, '_blank')
  if (!win || win.closed) {
    window.location.assign(url)
    return true
  }
  try {
    win.opener = null
  } catch {
    // 部分浏览器禁止改写 opener。
  }
  return true
}

export async function launchCheckout(checkout, handlers = {}) {
  if (!checkout) {
    throw new Error('支付渠道未返回有效的支付指令')
  }
  const url = checkoutRedirectUrl(checkout)
  const mode = checkout.mode || (url ? 'redirect' : '')
  if (mode === 'redirect' && url) {
    openCheckoutWindow(url)
    return 'redirect'
  }
  if (mode === 'form' && checkout.form_action) {
    submitGatewayForm(checkout)
    return 'form'
  }
  if (mode === 'qr' && (checkout.qr_code_text || checkout.qr_code_url)) {
    if (typeof handlers.onQr === 'function') {
      await handlers.onQr(checkout)
      return 'qr'
    }
  }
  if (mode === 'sdk') {
    if (typeof handlers.onSdk === 'function') {
      await handlers.onSdk(checkout)
      return 'sdk'
    }
  }
  throw new Error('支付渠道未返回有效的支付指令')
}
