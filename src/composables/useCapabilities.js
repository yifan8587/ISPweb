import { computed } from 'vue'
import { useAuthStore } from '@/store/auth'
import { userHasPermission } from '@/utils/permissions'

export function deriveCapabilities(user, override) {
  const fromPerms = {
    service_change: userHasPermission(user, 'service.change.manage'),
    order_create: userHasPermission(user, 'service.order.manage'),
    billing_pay: userHasPermission(user, 'billing.list.manage'),
    vps_manage: userHasPermission(user, 'resource.vps.manage'),
    edge_manage: userHasPermission(user, 'resource.edge.manage'),
    profile_update: userHasPermission(user, 'customer.detail.manage'),
    ticket_manage: userHasPermission(user, 'service.ticket.manage'),
  }
  return { ...fromPerms, ...(override || {}) }
}

export function useCapabilities() {
  const auth = useAuthStore()
  const caps = computed(() => deriveCapabilities(auth.user, auth.capabilities))
  return { caps }
}
