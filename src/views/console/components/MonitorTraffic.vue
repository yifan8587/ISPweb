<template>
  <section class="monitor-traffic" :aria-busy="loading">
    <div v-if="data" class="monitor-status">
      <div class="status-main">
        <el-tag size="small" :type="statusMeta.tagType" effect="plain">{{ statusMeta.label }}</el-tag>
        <span v-if="data.data_source" class="data-source">数据源：{{ sourceLabel }}</span>
        <span v-if="data.period" class="period">周期：{{ data.period }}</span>
      </div>
      <span v-if="data.updated_at" class="updated-at">采集于 {{ formatTime(data.updated_at) }}</span>
    </div>

    <el-alert
      v-if="data && !isOk"
      class="status-alert"
      :type="statusMeta.alertType"
      :closable="false"
      show-icon
      :title="statusMeta.title"
      :description="data.message || statusMeta.description"
    />

    <div v-if="isOk && data?.summary" class="summary" aria-label="流量汇总">
      <div class="summary-item">
        <span>入站总量</span>
        <strong>{{ metric(data.summary.in_total_gb, ' GB') }}</strong>
      </div>
      <div class="summary-item">
        <span>出站总量</span>
        <strong>{{ metric(data.summary.out_total_gb, ' GB') }}</strong>
      </div>
      <div class="summary-item">
        <span>峰值</span>
        <strong>{{ metric(data.summary.peak_mbps, ' Mbps') }}</strong>
      </div>
      <div class="summary-item">
        <span>P95</span>
        <strong>{{ metric(data.summary.p95_mbps, ' Mbps') }}</strong>
      </div>
      <div class="summary-item">
        <span>平均</span>
        <strong>{{ metric(data.summary.avg_mbps, ' Mbps') }}</strong>
      </div>
      <div class="summary-item">
        <span>带宽限额</span>
        <strong>{{ metric(data.bandwidth_limit_mbps, ' Mbps') }}</strong>
      </div>
    </div>

    <div
      v-if="isOk && hasSeries"
      v-loading="loading"
      class="chart-canvas"
      aria-label="流量时间序列图"
    >
      <v-chart class="traffic-chart" :option="chartOption" autoresize />
    </div>

    <el-empty v-else-if="!loading" :description="emptyDescription" :image-size="72" />
  </section>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  CanvasRenderer,
])

const props = defineProps({
  data: Object,
  loading: Boolean,
})

const statusMap = {
  ok: {
    label: '数据正常',
    tagType: 'success',
    alertType: 'success',
    title: '流量监控数据正常',
    description: '',
  },
  not_configured: {
    label: '未配置',
    tagType: 'warning',
    alertType: 'warning',
    title: '尚未配置流量监控',
    description: '此服务尚未接入流量采集，请完成监控配置后再查看数据。',
  },
  no_data: {
    label: '暂无数据',
    tagType: 'info',
    alertType: 'info',
    title: '所选时间范围内暂无流量数据',
    description: '服务已接入监控，但当前时间范围内没有可用采样。',
  },
  unavailable: {
    label: '暂不可用',
    tagType: 'danger',
    alertType: 'error',
    title: '流量监控暂不可用',
    description: '监控服务暂时无法返回数据，请稍后刷新。',
  },
}

const isOk = computed(() => props.data?.status === 'ok')
const statusMeta = computed(() => statusMap[props.data?.status] || {
  label: '状态未知',
  tagType: 'info',
  alertType: 'info',
  title: '流量监控状态未知',
  description: '未收到可识别的流量监控状态。',
})
const series = computed(() => (Array.isArray(props.data?.series) ? props.data.series : []))
const hasSeries = computed(() => series.value.length > 0)
const sourceLabel = computed(() => ({
  zabbix: 'Zabbix',
}[props.data?.data_source] || props.data?.data_source))
const emptyDescription = computed(() => {
  if (props.data?.status === 'not_configured') return '当前服务尚未配置流量监控'
  if (props.data?.status === 'unavailable') return '流量监控暂不可用'
  if (props.data?.status === 'no_data') return '所选时间范围内暂无流量数据'
  return '暂无流量监控数据'
})

const chartOption = computed(() => {
  const rows = series.value
  const x = rows.map((row) => row.time)
  const inSeries = rows.map((row) => asNumber(row.in_mbps))
  const outSeries = rows.map((row) => asNumber(row.out_mbps))
  const p95 = asNumber(props.data?.summary?.p95_mbps)
  const limit = asNumber(props.data?.bandwidth_limit_mbps)

  const markLineData = []
  if (p95 !== null) {
    markLineData.push({
      yAxis: p95,
      label: {
        formatter: `P95 ${p95.toFixed(2)} Mbps`,
        position: 'insideEndTop',
        color: '#F56C6C',
        fontSize: 11,
      },
      lineStyle: { color: '#F56C6C', type: 'dashed', width: 1.5 },
    })
  }
  if (limit !== null && limit > 0) {
    markLineData.push({
      yAxis: limit,
      label: {
        formatter: `限额 ${limit.toFixed(2)} Mbps`,
        position: 'insideEndTop',
        color: '#E6A23C',
        fontSize: 11,
      },
      lineStyle: { color: '#E6A23C', type: 'dotted', width: 1.5 },
    })
  }

  const markLine = markLineData.length
    ? { silent: true, symbol: 'none', data: markLineData }
    : undefined

  return {
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value) => (value == null ? '-' : `${Number(value).toFixed(2)} Mbps`),
    },
    legend: {
      data: ['入站 (Inbound)', '出站 (Outbound)'],
      top: 0,
      right: 8,
      textStyle: { fontSize: 11 },
    },
    grid: { left: 52, right: 16, top: 28, bottom: 40 },
    xAxis: {
      type: 'category',
      data: x,
      boundaryGap: false,
      axisLabel: { fontSize: 10, formatter: formatAxisTime },
    },
    yAxis: {
      type: 'value',
      name: 'Mbps',
      nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 10, formatter: formatAxisValue },
    },
    dataZoom: [
      { type: 'inside' },
      { type: 'slider', height: 16, bottom: 8 },
    ],
    series: [
      {
        name: '入站 (Inbound)',
        type: 'line',
        smooth: true,
        showSymbol: false,
        areaStyle: { opacity: 0.12 },
        lineStyle: { width: 1.5 },
        itemStyle: { color: '#409EFF' },
        data: inSeries,
        markLine,
      },
      {
        name: '出站 (Outbound)',
        type: 'line',
        smooth: true,
        showSymbol: false,
        areaStyle: { opacity: 0.12 },
        lineStyle: { width: 1.5 },
        itemStyle: { color: '#67C23A' },
        data: outSeries,
      },
    ],
  }
})

function metric(value, suffix = '') {
  const number = asNumber(value)
  if (number === null) return '—'
  return `${number.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}${suffix}`
}

function asNumber(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (number) => String(number).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function formatAxisTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (number) => String(number).padStart(2, '0')
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function formatAxisValue(value) {
  if (value == null || value === '') return ''
  const number = Number(value)
  return Number.isFinite(number) ? number.toFixed(2) : value
}
</script>

<style scoped>
.monitor-traffic {
  min-width: 0;
}
.monitor-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  color: var(--ce-muted);
  font-size: 12px;
}
.status-main {
  display: flex;
  min-width: 0;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.data-source,
.period,
.updated-at {
  white-space: nowrap;
}
.status-alert {
  margin-bottom: 12px;
}
.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}
.summary-item {
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--ce-border);
  border-radius: 10px;
  background: var(--ce-surface);
}
.summary-item span {
  display: block;
  overflow: hidden;
  color: var(--ce-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.summary-item strong {
  display: block;
  margin-top: 5px;
  overflow: hidden;
  color: var(--ce-text);
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chart-canvas {
  width: 100%;
  min-height: 300px;
  padding: 8px 4px 4px;
  border: 1px solid var(--ce-border);
  border-radius: 10px;
  background: var(--ce-surface);
}
.traffic-chart {
  width: 100%;
  height: 300px;
}
@media (max-width: 600px) {
  .monitor-status {
    align-items: flex-start;
    flex-direction: column;
  }
  .summary {
    grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
  }
  .traffic-chart {
    height: 260px;
  }
}
</style>
