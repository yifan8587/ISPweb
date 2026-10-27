import { createGuardedRequest } from '../../src/utils/urlguard.js'

const [secret, method, path, query, body, timestamp, nonce, channel] = process.argv.slice(2)
const result = await createGuardedRequest({
  secret,
  method,
  path,
  query,
  body: new TextEncoder().encode(body),
  timestamp,
  nonce,
  channel,
})
process.stdout.write(JSON.stringify({ url: result.url, bodyHash: result.bodyHash }))
