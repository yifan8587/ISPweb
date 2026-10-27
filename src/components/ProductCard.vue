<template>
  <div class="prod-card" :class="{ featured: isHot }" @click="$emit('order', product)">
    <div class="pc-head">
      <el-tag size="small" :type="product.category === 'vps' ? 'primary' : 'success'" effect="dark" round>
        {{ categoryLabel(product) }}
      </el-tag>
      <div class="pc-corner">
        <span v-if="isHot" class="pc-hot">🔥 热卖</span>
        <span class="pc-seller" :class="{ own: !hasSupplier }">{{ sellerText }}</span>
      </div>
    </div>
    <div class="pc-loc">{{ locText }}</div>

    <ul class="pc-spec">
      <template v-if="product.category === 'vps'">
        <li><el-icon><Cpu /></el-icon> {{ product.cpu_cores }} vCPU</li>
        <li><el-icon><Coin /></el-icon> {{ ramText(product.ram_mb) }} 内存</li>
        <li><el-icon><Files /></el-icon> {{ product.disk_gb }} GB</li>
        <li><el-icon><Promotion /></el-icon> {{ product.bandwidth_mbps }}Mbps · {{ product.ip_count }} IP</li>
      </template>
      <template v-else>
        <li><el-icon><Promotion /></el-icon> {{ product.bandwidth_mbps }}Mbps</li>
        <li><el-icon><Postcard /></el-icon> {{ product.ip_count }} IP</li>
      </template>
    </ul>

    <div class="pc-sample" :class="{ 'is-empty': !sampleIpText }">
      <span v-if="sampleIpText" class="pc-ip-value">{{ sampleIpText }}</span>
    </div>

    <div class="pc-tags">
      <el-tag
        v-for="t in networkTypes"
        :key="'nt-'+t.value"
        size="small"
        effect="plain"
        :type="t.value === 'home_broadband' ? 'warning' : 'primary'"
      >
        {{ t.label }}
      </el-tag>
      <el-tag v-for="t in asnNatures" :key="'asn-'+t.value" size="small" effect="plain" type="info">
        {{ t.label }}
      </el-tag>
      <el-tag v-if="showNat" size="small" type="warning" effect="plain">NAT IP</el-tag>
      <el-tag v-for="a in uniqueIpAttrs" :key="a" size="small" effect="plain">
        {{ ipAttrLabel(a) }}
      </el-tag>
    </div>

    <div class="pc-foot">
      <div class="pc-price">
        <span class="amount">{{ money(product.monthly_price, product.currency) }}</span>
        <span class="unit">/月</span>
      </div>
      <el-button type="primary" size="small">立即选购</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  asnNatureLabel, categoryLabel, ipAttrLabel, isHotSale, isNatDelivery, money,
  networkTypeLabel, productLocationText, ramText, sellerLabel, sortByCode, sortNetworkTypes,
  ASN_NATURE_ORDER, IP_ATTR_ORDER,
} from '@/utils/format'

const props = defineProps({ product: { type: Object, required: true } })
defineEmits(['order'])

const locText = computed(() => productLocationText(props.product))
const isHot = computed(() => isHotSale(props.product))
const sellerText = computed(() => sellerLabel(props.product))
const hasSupplier = computed(() => sellerText.value !== '自营')
const showNat = computed(() => isNatDelivery(props.product))

const sampleIps = computed(() =>
  String(props.product.sample_ip || '')
    .split(/[,，\s]+/)
    .map((s) => s.trim())
    .filter(Boolean),
)
const sampleIpText = computed(() => sampleIps.value.join(' / '))

const networkTypes = computed(() => {
  const p = props.product
  let list = []
  if (Array.isArray(p.network_types) && p.network_types.length) {
    list = p.network_types.map((t) => ({
      value: t.value || t.code,
      label: t.label || t.name || networkTypeLabel(t.value || t.code),
    }))
  } else if (p.network_type) {
    list = [{ value: p.network_type, label: p.network_type_label || networkTypeLabel(p.network_type) }]
  }
  return sortNetworkTypes(list)
})
const asnNatures = computed(() => {
  const p = props.product
  if (Array.isArray(p.asn_natures) && p.asn_natures.length) {
    return sortByCode(p.asn_natures.map((t) => ({
      value: t.value,
      label: t.label || asnNatureLabel(t.value),
    })), ASN_NATURE_ORDER)
  }
  if (p.asn_nature) {
    return [{ value: p.asn_nature, label: p.asn_nature_label || asnNatureLabel(p.asn_nature) }]
  }
  return []
})
const uniqueIpAttrs = computed(() => {
  const raw = props.product.ip_attributes || []
  const seen = new Set()
  const out = []
  for (const item of raw) {
    const value = item && typeof item === 'object' ? (item.value ?? item.label ?? '') : item
    const key = String(value ?? '').trim().toLowerCase()
    if (!key || seen.has(key)) continue
    seen.add(key)
    out.push(value)
  }
  return sortByCode(out, IP_ATTR_ORDER)
})
</script>

<style scoped>
.prod-card {
  position: relative;
  height: 100%;
  background: #fff;
  border: 1px solid var(--ce-border);
  border-radius: 10px;
  padding: 14px 14px 12px;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s;
}
.prod-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--ce-shadow);
  border-color: #bfdbfe;
}
.prod-card.featured {
  border-color: var(--ce-primary);
}
.pc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.pc-corner {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  flex-shrink: 0;
  min-width: 0;
}
.pc-hot {
  font-size: 12px;
  font-weight: 700;
  color: #e11d48;
  white-space: nowrap;
  line-height: 1.2;
}
.pc-seller {
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  font-weight: 650;
  line-height: 18px;
  padding: 1px 7px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #475569;
}
.pc-seller.own {
  background: #eff6ff;
  color: var(--ce-primary);
}
.pc-loc {
  font-size: 12px;
  color: var(--ce-muted);
  line-height: 1.35;
  min-height: 1.35em;
  margin-bottom: 8px;
}
.pc-spec {
  list-style: none;
  padding: 0;
  margin: 0 0 8px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-content: start;
  gap: 6px 8px;
  min-height: 22px;
}
.pc-sample {
  min-height: 22px;
  margin: auto 0 8px;
}
.pc-sample.is-empty {
  visibility: hidden;
}
.pc-ip-value {
  display: block;
  min-height: 1.2em;
  line-height: 1.4;
  font-size: 13px;
  font-weight: 600;
  word-break: break-all;
  color: var(--ce-text);
}
.pc-spec li {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--ce-text-secondary);
}
.pc-spec .el-icon { color: var(--ce-primary); }
.pc-tags {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 4px;
  margin-bottom: 10px;
  min-height: 24px;
}
.pc-foot {
  margin-top: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid var(--ce-border);
  padding-top: 10px;
}
.pc-price .amount {
  font-size: 20px;
  font-weight: 800;
  color: var(--ce-price);
}
.pc-price .unit {
  font-size: 12px;
  color: var(--ce-muted);
  margin-left: 2px;
}
</style>
