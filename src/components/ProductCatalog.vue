<template>
  <div class="mall">
    <div class="mall-bar">
      <div class="ce-container ce-container--wide mall-bar-inner">
        <el-radio-group v-model="filters.category" size="small" @change="onCategory">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="vps">VPS</el-radio-button>
          <el-radio-button label="edge">公网对接</el-radio-button>
        </el-radio-group>
        <el-input
          v-model="filters.search"
          placeholder="搜索产品名称"
          clearable
          size="small"
          class="mall-search"
          :prefix-icon="Search"
          @keyup.enter="reload"
          @clear="reload"
        />
        <div class="mall-meta">
          <span class="muted">共 {{ total }} 款</span>
          <el-select v-model="ordering" size="small" class="mall-order" @change="reload">
            <el-option label="推荐排序" value="sort_order" />
            <el-option label="价格从低到高" value="monthly_price" />
            <el-option label="价格从高到低" value="-monthly_price" />
            <el-option label="最新上架" value="-created_at" />
          </el-select>
        </div>
      </div>
    </div>

    <div class="mall-filters">
      <div class="ce-container ce-container--wide">
        <div class="filter-row">
          <span class="fk">网络类型</span>
          <button type="button" class="chip" :class="{ on: !filters.network_type }" @click="setFilter('network_type', '')">不限</button>
          <button
            v-for="t in networkTypes"
            :key="t.code"
            type="button"
            class="chip"
            :class="{ on: filters.network_type === t.code }"
            @click="setFilter('network_type', t.code)"
          >{{ t.name }}</button>
        </div>
        <div class="filter-row">
          <span class="fk">IP 属性</span>
          <button type="button" class="chip" :class="{ on: !filters.ip_attribute }" @click="setFilter('ip_attribute', '')">不限</button>
          <button type="button" class="chip" :class="{ on: filters.ip_attribute === 'broadcast' }" @click="setFilter('ip_attribute', 'broadcast')">广播</button>
          <button type="button" class="chip" :class="{ on: filters.ip_attribute === 'native' }" @click="setFilter('ip_attribute', 'native')">原生</button>
        </div>
        <div class="filter-row">
          <span class="fk">ASN 性质</span>
          <button type="button" class="chip" :class="{ on: !filters.asn_nature }" @click="setFilter('asn_nature', '')">不限</button>
          <button
            v-for="t in asnNatures"
            :key="t.code"
            type="button"
            class="chip"
            :class="{ on: filters.asn_nature === t.code }"
            @click="setFilter('asn_nature', t.code)"
          >{{ t.name }}</button>
        </div>
        <div class="filter-row">
          <span class="fk">地区</span>
          <el-select v-model="filters.region" placeholder="全部区域" clearable size="small" class="loc" @change="onRegion">
            <el-option v-for="r in regions" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
          <el-select v-model="filters.country" placeholder="全部国家" clearable filterable size="small" class="loc" @change="onCountry">
            <el-option v-for="c in filteredCountries" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-select v-model="filters.city" placeholder="全部城市" clearable filterable size="small" class="loc" @change="reload">
            <el-option v-for="c in filteredCities" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-button v-if="hasActiveFilters" text type="primary" size="small" @click="resetFilters">重置</el-button>
        </div>
      </div>
    </div>

    <div v-if="quickCountries.length" class="quick-bar">
      <div class="ce-container ce-container--wide">
        <div class="filter-row">
          <span class="fk">快速查找</span>
          <button type="button" class="chip" :class="{ on: !filters.country }" @click="pickCountry('')">全部</button>
          <button
            v-for="c in quickCountries"
            :key="c.id"
            type="button"
            class="chip"
            :class="{ on: String(filters.country) === String(c.country) }"
            @click="pickCountry(c)"
          >{{ c.name }}</button>
        </div>
      </div>
    </div>

    <div class="ce-container ce-container--wide mall-list">
      <div v-loading="loading" class="grid">
        <ProductCard v-for="p in products" :key="p.id" :product="p" @order="goOrder" />
        <el-empty v-if="!loading && loadError" description="暂时无法获取产品，请稍后重试" style="grid-column:1/-1" />
        <el-empty v-else-if="!loading && !products.length" description="没有符合条件的产品" style="grid-column:1/-1" />
      </div>
      <el-pagination
        v-if="total > pageSize"
        class="pager"
        background
        layout="prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="onPage"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { getLocations, getProducts } from '@/api'
import ProductCard from '@/components/ProductCard.vue'
import { sortNetworkTypes } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const products = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)
const loading = ref(false)
const loadError = ref(false)
const ordering = ref('sort_order')

const regions = ref([])
const countries = ref([])
const cities = ref([])
const quickCountries = ref([])
const networkTypes = ref([
  { code: 'idc', name: 'IDC' },
  { code: 'home_broadband', name: '家宽' },
])
const asnNatures = ref([
  { code: 'non_isp', name: '非ISP' },
  { code: 'isp', name: '单ISP' },
  { code: 'dual_isp', name: '双ISP' },
])

const filters = reactive({
  category: route.query.category || '',
  region: '',
  country: '',
  city: '',
  network_type: '',
  ip_attribute: '',
  asn_nature: '',
  search: '',
})

const filteredCountries = computed(() =>
  filters.region ? countries.value.filter((c) => c.region === filters.region) : countries.value)
const filteredCities = computed(() =>
  filters.country ? cities.value.filter((c) => c.country === filters.country) : cities.value)
const hasActiveFilters = computed(() =>
  Boolean(filters.region || filters.country || filters.city || filters.network_type || filters.ip_attribute || filters.asn_nature || filters.search))

function onRegion() {
  filters.country = ''
  filters.city = ''
  reload()
}
function onCountry() {
  filters.city = ''
  reload()
}
function pickCountry(item) {
  const id = item && item.country ? item.country : ''
  const same = String(filters.country) === String(id)
  filters.country = same ? '' : id
  filters.city = ''
  if (!same && item?.region) filters.region = item.region
  reload()
}
function setFilter(key, value) {
  filters[key] = filters[key] === value ? '' : value
  reload()
}
function onCategory() {
  syncCategoryQuery()
  reload()
}
function syncCategoryQuery() {
  const next = { ...route.query }
  if (filters.category) next.category = filters.category
  else delete next.category
  router.replace({ query: next })
}

async function load() {
  loading.value = true
  loadError.value = false
  try {
    const params = { page: page.value, page_size: pageSize.value, ordering: ordering.value }
    for (const k of ['category', 'region', 'country', 'city', 'network_type', 'ip_attribute', 'asn_nature', 'search']) {
      if (filters[k]) params[k] = filters[k]
    }
    const res = await getProducts(params)
    products.value = res.results || []
    total.value = res.count || 0
  } catch {
    products.value = []
    total.value = 0
    loadError.value = true
  } finally {
    loading.value = false
  }
}
function reload() {
  page.value = 1
  load()
}
function onPage(p) {
  page.value = p
  load()
}
function resetFilters() {
  Object.assign(filters, {
    region: '', country: '', city: '',
    network_type: '', ip_attribute: '', asn_nature: '', search: '',
  })
  reload()
}
function goOrder(p) {
  router.push({ name: 'product-detail', params: { id: p.id } })
}

watch(() => route.query.category, (v) => {
  const next = v || ''
  if (filters.category !== next) {
    filters.category = next
    reload()
  }
})

onMounted(async () => {
  try {
    const res = await getLocations()
    const d = res.data || res
    regions.value = d.regions || []
    countries.value = d.countries || []
    cities.value = d.cities || []
    quickCountries.value = d.quick_countries || []
    if (Array.isArray(d.network_types) && d.network_types.length) {
      networkTypes.value = sortNetworkTypes(d.network_types).map((t) => ({
        code: t.code || t.value,
        name: t.name || t.label,
      }))
    }
  } catch {
    /* ignore */
  }
  load()
})
</script>

<style scoped>
.mall {
  background: #f5f5f5;
  min-height: 64vh;
}
.mall-bar {
  background: #fff;
  border-bottom: 1px solid var(--ce-border);
}
.mall-bar-inner {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-top: 12px;
  padding-bottom: 12px;
}
.mall-search {
  max-width: 280px;
  flex: 1;
  min-width: 140px;
}
.mall-order { width: 148px; }
.mall-meta {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}
.mall-filters {
  background: #fff;
  border-bottom: 1px solid var(--ce-border);
  padding: 8px 0 10px;
}
.quick-bar {
  background: #fff;
  border-bottom: 1px solid var(--ce-border);
  padding: 4px 0 8px;
}
.filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 32px;
  padding: 3px 0;
}
.fk {
  width: 72px;
  flex: 0 0 72px;
  color: var(--ce-muted);
  font-size: 13px;
  font-weight: 650;
}
.chip {
  border: 0;
  background: transparent;
  color: var(--ce-text-secondary);
  font-size: 13px;
  padding: 3px 10px;
  border-radius: 4px;
  cursor: pointer;
}
.chip:hover { color: var(--ce-primary); }
.chip.on {
  background: var(--ce-primary-soft);
  color: var(--ce-primary);
  font-weight: 700;
}
.loc { width: 140px; }
.mall-list {
  padding-top: 16px;
  padding-bottom: 48px;
}
.grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  justify-content: stretch;
  align-items: stretch;
  gap: 16px;
  min-height: 180px;
}
.pager {
  margin-top: 22px;
  justify-content: center;
}
@media (min-width: 768px) {
  .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (min-width: 1200px) {
  .grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 860px) {
  .mall-bar-inner { flex-wrap: wrap; }
  .mall-meta { margin-left: 0; width: 100%; justify-content: space-between; }
}
@media (max-width: 720px) {
  .mall-search, .mall-order { max-width: none; width: 100%; }
  .mall-meta { flex-wrap: wrap; }
  .fk { flex-basis: 100%; }
}
@media (max-width: 560px) {
  .loc { width: 100%; }
}
</style>
