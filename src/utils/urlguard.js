// 生产构建才会开启。算法须与 deploy/gate/urlguard_crypto.py 保持一致。

function webcrypto() {
  const cryptoApi = globalThis.crypto
  if (!cryptoApi || !cryptoApi.subtle) {
    throw new Error('当前页面不是安全上下文，无法计算访问签名')
  }
  return cryptoApi
}

function guardEnv() {
  let enabled = ''
  let secret = ''
  try {
    enabled = import.meta.env.VITE_URL_GUARD
    secret = import.meta.env.VITE_URL_GUARD_SECRET
  } catch {
    enabled = ''
    secret = ''
  }
  return {
    enabled: enabled === '1' && !!secret,
    secret: secret || '',
  }
}

function bytesToHex(bytes) {
  let hex = ''
  for (const byte of bytes) hex += byte.toString(16).padStart(2, '0')
  return hex
}

function encodeRfc3986(value) {
  return encodeURIComponent(String(value)).replace(/[!'()*]/g, (ch) => {
    return `%${ch.charCodeAt(0).toString(16).toUpperCase()}`
  })
}

export function canonicalQuery(searchParams, extra) {
  const pairs = []
  const seen = new Set()
  const add = (key, value) => {
    const name = String(key)
    if (seen.has(name)) throw new Error('严格模式拒绝重复参数')
    seen.add(name)
    pairs.push([name, value == null ? '' : String(value)])
  }
  if (searchParams) {
    for (const [key, value] of searchParams.entries()) add(key, value)
  }
  if (extra && typeof extra === 'object') {
    for (const [key, value] of Object.entries(extra)) {
      if (value === undefined || value === null) continue
      if (Array.isArray(value)) {
        if (value.length !== 1) throw new Error('严格模式拒绝重复参数')
        add(key, value[0])
      } else {
        add(key, value)
      }
    }
  }
  pairs.sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
  return pairs.map(([key, value]) => `${encodeRfc3986(key)}=${encodeRfc3986(value)}`).join('&')
}

async function sha256Hex(bytes) {
  const digest = await webcrypto().subtle.digest('SHA-256', bytes)
  return bytesToHex(new Uint8Array(digest))
}

async function hmacHex(secret, message) {
  const cryptoApi = webcrypto()
  const key = await cryptoApi.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  )
  const sig = await cryptoApi.subtle.sign('HMAC', key, new TextEncoder().encode(message))
  return bytesToHex(new Uint8Array(sig))
}

async function obfuscateEncode(text, secret) {
  const cryptoApi = webcrypto()
  const key = new Uint8Array(await cryptoApi.subtle.digest('SHA-256', new TextEncoder().encode(secret)))
  const raw = new TextEncoder().encode(text)
  const mixed = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i += 1) mixed[i] = raw[i] ^ key[i % key.length]
  let binary = ''
  const step = 0x8000
  for (let i = 0; i < mixed.length; i += step) {
    binary += String.fromCharCode(...mixed.subarray(i, i + step))
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function randomNonce() {
  const bytes = new Uint8Array(16)
  webcrypto().getRandomValues(bytes)
  return bytesToHex(bytes)
}

function encodeBody(data) {
  if (data == null || data === '') {
    return { bytes: new Uint8Array(), raw: null, contentType: '' }
  }
  if (typeof data === 'string') {
    return { bytes: new TextEncoder().encode(data), raw: data, contentType: '' }
  }
  if (typeof FormData !== 'undefined' && data instanceof FormData) {
    throw new Error('严格模式不支持表单上传')
  }
  if (typeof data === 'object') {
    const raw = JSON.stringify(data)
    return {
      bytes: new TextEncoder().encode(raw),
      raw,
      contentType: 'application/json;charset=UTF-8',
    }
  }
  throw new Error('严格模式无法签名该请求体')
}

function setHeader(headers, name, value) {
  if (!headers) return
  if (typeof headers.set === 'function') headers.set(name, value)
  else headers[name] = value
}

function joinUrl(base, url) {
  if (/^https?:\/\//i.test(url)) return url
  if (!base) return url
  if (url.startsWith('/')) return `${String(base).replace(/\/$/, '')}${url}`
  return `${String(base).replace(/\/$/, '')}/${url}`
}

export async function createGuardedRequest({
  secret,
  method,
  path,
  query = '',
  body = new Uint8Array(),
  timestamp,
  nonce,
  channel = 'http',
}) {
  const verb = String(method || 'GET').toUpperCase()
  const payload = JSON.stringify({ v: 1, m: verb, p: path, q: query })
  const token = await obfuscateEncode(payload, secret)
  const ts = String(timestamp ?? Math.floor(Date.now() / 1000))
  const n = nonce || randomNonce()
  const bodyHash = await sha256Hex(body)
  const mac = await hmacHex(secret, `${verb}\n${token}\n${bodyHash}\n${ts}\n${n}`)
  const prefix = channel === 'ws' ? '/_gws/' : '/_g/'
  return {
    url: `${prefix}${token}?_t=${ts}&_n=${n}&_h=${mac}`,
    token,
    timestamp: ts,
    nonce: n,
    bodyHash,
  }
}

export async function guardWebSocket(path, query) {
  const { enabled, secret } = guardEnv()
  if (!enabled) return null
  const guarded = await createGuardedRequest({
    secret,
    method: 'GET',
    path,
    query,
    body: new Uint8Array(),
    channel: 'ws',
  })
  return guarded.url
}

export async function applyUrlGuard(config) {
  const { enabled, secret } = guardEnv()
  if (!enabled) return config
  if (!config._guardOriginal) {
    config._guardOriginal = {
      baseURL: config.baseURL,
      url: config.url,
      params: config.params && typeof config.params === 'object' ? { ...config.params } : config.params,
      data: config.data,
    }
  }
  const src = config._guardOriginal
  const method = String(config.method || 'get').toUpperCase()
  const joined = joinUrl(src.baseURL || '', src.url || '')
  const parsed = new URL(joined, 'http://ispweb.local')
  if (!parsed.pathname.startsWith('/api/') && !parsed.pathname.startsWith('/ws/')) {
    throw new Error('严格模式只允许访问门户接口')
  }
  const query = canonicalQuery(parsed.searchParams, src.params)
  const encoded = encodeBody(src.data)
  const channel = parsed.pathname.startsWith('/ws/') ? 'ws' : 'http'
  const guarded = await createGuardedRequest({
    secret,
    method,
    path: parsed.pathname,
    query,
    body: encoded.bytes,
    channel,
  })
  config.baseURL = ''
  config.url = guarded.url
  delete config.params
  if (encoded.raw != null) {
    config.data = encoded.raw
    if (encoded.contentType) setHeader(config.headers, 'Content-Type', encoded.contentType)
  }
  return config
}
