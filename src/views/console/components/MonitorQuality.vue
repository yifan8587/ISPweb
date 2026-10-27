<template>
  <section class="monitor-quality" :aria-busy="loading">
    <div v-if="data" class="monitor-status">
      <div class="status-main">
        <el-tag size="small" :type="statusMeta.tagType" effect="plain">{{ statusMeta.label }}</el-tag>
        <span v-if="data.data_source" class="data-source">数据源：{{ sourceLabel }}</span>
        <span v-if="data.node_name" class="data-source">节点：{{ data.node_name }}</span>
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

    <template v-if="showMetrics">
      <div class="summary" aria-label="链路质量汇总">
        <div class="summary-item">
          <span>当前延迟</span>
          <strong>{{ metric(currentLatency, ' ms') }}</strong>
        </div>
        <div class="summary-item">
          <span>平均延迟</span>
          <strong>{{ metric(averageLatency, ' ms') }}</strong>
        </div>
        <div class="summary-item">
          <span>最大延迟</span>
          <strong>{{ metric(maxLatency, ' ms') }}</strong>
        </div>
        <div class="summary-item">
          <span>可用性</span>
          <strong>{{ metric(availability, '%') }}</strong>
        </div>
      </div>
      <div class="current-details">
        <span>当前丢包：<b>{{ metric(currentPacketLoss, '%') }}</b></span>
        <span>当前抖动：<b>{{ metric(currentJitter, ' ms') }}</b></span>
      </div>
    </template>

    <div v-if="latencyPoints.length" class="chart-card" aria-label="延迟与丢包监控图表">
      <div class="chart-head">
        <span>延迟 / 丢包</span>
        <span v-if="latencyCaption" class="chart-caption">{{ latencyCaption }}</span>
      </div>
      <v-chart class="quality-chart" :option="latencyOption" autoresize />
    </div>

    <div v-if="trafficPoints.length" class="chart-card" aria-label="接口流量监控图表">
      <div class="chart-head">
        <span>接口流量</span>
        <span v-if="trafficCaption" class="chart-caption">{{ trafficCaption }}</span>
      </div>
      <v-chart class="quality-chart" :option="trafficOption" autoresize />
    </div>

    <el-empty v-if="!loading && !hasCharts" :description="emptyDescription" :image-size="72" />
  </section>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([
  BarChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
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
    title: '品质监控数据正常',
    description: '',
  },
  not_configured: {
    label: '未配置',
    tagType: 'warning',
    alertType: 'warning',
    title: '尚未配置品质监控',
    description: '此服务尚未接入链路质量探测，请完成监控配置后再查看数据。',
  },
  no_data: {
    label: '暂无数据',
    tagType: 'info',
    alertType: 'info',
    title: '所选时间范围内暂无品质数据',
    description: '服务已接入监控，但当前时间范围内没有可用探测结果。',
  },
  stale: {
    label: '数据过期',
    tagType: 'warning',
    alertType: 'warning',
    title: '品质监控数据已过期',
    description: '当前展示的是最近一次采集结果，新的探测数据尚未到达。',
  },
}

const isOk = computed(() => props.data?.status === 'ok')
const statusMeta = computed(() => statusMap[props.data?.status] || {
  label: '状态未知',
  tagType: 'info',
  alertType: 'info',
  title: '品质监控状态未知',
  description: '未收到可识别的品质监控状态。',
})
const series = computed(() => (Array.isArray(props.data?.series) ? props.data.series : []))
const latencyChart = computed(() => props.data?.latency_chart || null)
const trafficChart = computed(() => props.data?.traffic_chart || null)
const latencyPoints = computed(() => (
  Array.isArray(latencyChart.value?.points) ? latencyChart.value.points : []
))
const trafficPoints = computed(() => (
  Array.isArray(trafficChart.value?.points) ? trafficChart.value.points : []
))
const hasCharts = computed(() => latencyPoints.value.length > 0 || trafficPoints.value.length > 0)
const latencyCaption = computed(() => {
  const name = latencyChart.value?.target_name || ''
  const address = latencyChart.value?.target_address || ''
  if (name && address) return `${name} · ${address}`
  return name || address
})
const trafficCaption = computed(() => trafficChart.value?.interface_name || '')
const latencyOption = computed(() => buildLatencyOption(latencyPoints.value, latencyChart.value?.bucket))
const trafficOption = computed(() => buildTrafficOption(trafficPoints.value, trafficChart.value?.bucket))
const sourceLabel = computed(() => ({
  vpop_telemetry: 'vPOP Telemetry',
  vpop_node: 'vPOP 节点品质监控',
}[props.data?.data_source] || props.data?.data_source))
const currentLatency = computed(() => firstNumber([props.data?.current], ['latency_ms']))
const currentPacketLoss = computed(() => firstNumber([props.data?.current], ['packet_loss_pct']))
const currentJitter = computed(() => firstNumber([props.data?.current], ['jitter_ms']))
const averageLatency = computed(() => (
  firstNumber([props.data?.summary], ['avg_latency_ms', 'latency_avg_ms', 'average_latency_ms'])
  ?? averageOf(series.value, 'latency_ms')
))
const maxLatency = computed(() => (
  firstNumber([props.data?.summary], ['max_latency_ms', 'latency_max_ms'])
  ?? maxOf(series.value, 'latency_ms')
))
const availability = computed(() => (
  firstNumber(
    [props.data?.current, props.data?.summary],
    ['availability_pct', 'avg_availability_pct', 'average_availability_pct'],
  )
  ?? averageOf(series.value, 'availability_pct')
))
const showMetrics = computed(() => (
  (isOk.value || props.data?.status === 'stale')
  && Boolean(
    props.data?.current
    || series.value.length
    || asNumber(props.data?.summary?.sample_count) > 0
  )
))
const emptyDescription = computed(() => {
  if (props.data?.status === 'not_configured') return '当前服务尚未配置品质监控'
  if (props.data?.status === 'stale') return '暂无可展示的历史品质数据'
  if (props.data?.status === 'no_data') return '所选时间范围内暂无品质数据'
  return '暂无品质监控数据'
})

function firstNumber(sources, keys) {
  for (const source of sources) {
    for (const key of keys) {
      const number = asNumber(source?.[key])
      if (number !== null) return number
    }
  }
  return null
}

function averageOf(points, key) {
  const values = points
    .map((point) => asNumber(point?.[key]))
    .filter((value) => value !== null)
  if (!values.length) return null
  return values.reduce((total, value) => total + value, 0) / values.length
}

function maxOf(points, key) {
  const values = points
    .map((point) => asNumber(point?.[key]))
    .filter((value) => value !== null)
  return values.length ? Math.max(...values) : null
}

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

function isTimeBucket(bucket) {
  return bucket === 'minute' || bucket === 'hour'
}

function buildLatencyOption(points, bucket) {
  const timeAxis = isTimeBucket(bucket)
  return {
    grid: { left: 48, right: 48, top: 36, bottom: 56, containLabel: true },
    legend: { data: ['RTT 平均 ms', 'RTT 最大 ms', '丢包 %'], top: 0 },
    tooltip: { trigger: 'axis' },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0 },
      { type: 'slider', xAxisIndex: 0, bottom: 8, height: 18 },
    ],
    xAxis: timeAxis
      ? { type: 'time' }
      : { type: 'category', data: points.map((point) => point.bucket) },
    yAxis: [
      { type: 'value', name: 'ms', min: 0 },
      { type: 'value', name: '丢包 %', min: 0, max: 100 },
    ],
    series: [
      {
        name: 'RTT 平均 ms',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: points.map((point) => (timeAxis ? [point.bucket, point.rtt_avg_ms] : point.rtt_avg_ms)),
      },
      {
        name: 'RTT 最大 ms',
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { type: 'dashed' },
        data: points.map((point) => (timeAxis ? [point.bucket, point.rtt_max_ms] : point.rtt_max_ms)),
      },
      {
        name: '丢包 %',
        type: 'bar',
        yAxisIndex: 1,
        itemStyle: { color: '#f56c6c' },
        data: points.map((point) => (timeAxis ? [point.bucket, point.loss_pct] : point.loss_pct)),
      },
    ],
  }
}

function buildTrafficOption(points, bucket) {
  const timeAxis = isTimeBucket(bucket)
  const mbps = (value) => (asNumber(value) || 0) / 1e6
  return {
    grid: { left: 48, right: 24, top: 36, bottom: 56, containLabel: true },
    legend: { data: ['RX 平均 Mbps', 'TX 平均 Mbps', 'RX 峰值 Mbps', 'TX 峰值 Mbps'], top: 0 },
    tooltip: { trigger: 'axis' },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0 },
      { type: 'slider', xAxisIndex: 0, bottom: 8, height: 18 },
    ],
    xAxis: timeAxis
      ? { type: 'time' }
      : { type: 'category', data: points.map((point) => point.bucket) },
    yAxis: { type: 'value', name: 'Mbps', min: 0 },
    series: [
      {
        name: 'RX 平均 Mbps',
        type: 'line',
        smooth: true,
        showSymbol: false,
        areaStyle: { opacity: 0.08 },
        data: points.map((point) => (timeAxis ? [point.bucket, mbps(point.rx_bps_avg)] : mbps(point.rx_bps_avg))),
      },
      {
        name: 'TX 平均 Mbps',
        type: 'line',
        smooth: true,
        showSymbol: false,
        areaStyle: { opacity: 0.08 },
        data: points.map((point) => (timeAxis ? [point.bucket, mbps(point.tx_bps_avg)] : mbps(point.tx_bps_avg))),
      },
      {
        name: 'RX 峰值 Mbps',
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { type: 'dashed' },
        data: points.map((point) => (timeAxis ? [point.bucket, mbps(point.rx_bps_max)] : mbps(point.rx_bps_max))),
      },
      {
        name: 'TX 峰值 Mbps',
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { type: 'dashed' },
        data: points.map((point) => (timeAxis ? [point.bucket, mbps(point.tx_bps_max)] : mbps(point.tx_bps_max))),
      },
    ],
  }
}

function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (number) => String(number).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}
</script>

<style scoped>
.monitor-quality {
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
  margin-bottom: 10px;
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
.current-details {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
  color: var(--ce-text-secondary);
  font-size: 13px;
}
.current-details b {
  color: var(--ce-text);
}
.chart-card {
  margin-bottom: 14px;
  padding: 12px 12px 4px;
  border: 1px solid var(--ce-border);
  border-radius: 10px;
  background: var(--ce-surface);
}
.chart-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
  color: var(--ce-text);
  font-size: 13px;
  font-weight: 600;
}
.chart-caption {
  min-width: 0;
  overflow: hidden;
  color: var(--ce-muted);
  font-size: 12px;
  font-weight: 400;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.quality-chart {
  width: 100%;
  height: 320px;
}
@media (max-width: 600px) {
  .monitor-status {
    align-items: flex-start;
    flex-direction: column;
  }
  .summary {
    grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
  }
}
</style>
