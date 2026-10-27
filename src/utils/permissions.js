/** 与管理端 / 后端 permission_satisfies 对齐的精简判断 */

export function permissionSatisfies(held, required) {
  if (!required) return true
  if (held === required) return true
  if (required.endsWith('.view') && held === `${required.slice(0, -5)}.manage`) return true
  const h = held.split('.')
  const r = required.split('.')
  if (h.length === 2 && r.length >= 3 && h[0] === r[0] && h[1] === r[r.length - 1]) return true
  return false
}

export function userHasPermission(user, required) {
  if (!required) return true
  if (user?.is_superuser) return true
  const perms = user?.permissions || []
  return perms.some((held) => permissionSatisfies(held, required))
}
