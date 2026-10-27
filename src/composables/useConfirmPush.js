import { ElMessage, ElMessageBox } from 'element-plus'
import { pushEdgeToNode } from '@/api'

/**
 * 门户隧道下发：先 dry_run 预览，确认后再真正写入节点。
 * 与管理端 useConfirmPush 对齐；API 默认仍是真下发，由前端显式传 dry_run。
 */
export async function confirmPortalEdgePush(edgeId) {
  let preview
  try {
    preview = await pushEdgeToNode(edgeId, true)
  } catch {
    return { ok: false, stage: 'preview' }
  }
  const previewText = preview?.preview_text
    || '将把当前隧道配置写入节点并即时生效。确定继续？'
  try {
    await ElMessageBox.confirm(previewText, '确认下发到节点', {
      type: 'warning',
      confirmButtonText: '确认下发',
      cancelButtonText: '取消',
    })
  } catch {
    return { ok: false, stage: 'cancel', result: preview }
  }
  try {
    const res = await pushEdgeToNode(edgeId, false)
    const data = res?.data || {}
    if (data.apply_ok === false) {
      ElMessage.warning(res?.message || '节点已收到配置，但系统未确认生效')
      return { ok: false, stage: 'push', result: res }
    }
    ElMessage.success(res?.message || '已下发到节点并生效')
    return { ok: true, stage: 'push', result: res }
  } catch {
    return { ok: false, stage: 'push' }
  }
}
