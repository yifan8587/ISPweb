<template>
  <div class="info-page">
    <div class="ce-container ce-container--wide info-wrap">
      <aside class="info-nav">
        <h3>产品介绍</h3>
        <a href="#intro" @click.prevent="go('intro')">平台简介</a>
        <a href="#features" @click.prevent="go('features')">核心能力</a>
        <a href="#scenarios" @click.prevent="go('scenarios')">适用场景</a>
        <a href="#delivery" @click.prevent="go('delivery')">透明交付</a>
        <a href="#why" @click.prevent="go('why')">为什么选择我们</a>
      </aside>

      <article class="info-main">
        <section id="intro" class="info-block">
          <span class="ce-eyebrow">产品介绍</span>
          <h1>高性能 VPS 与公网对接</h1>
          <p>
            覆盖多区域节点，原生 / 广播 IP 任选，家宽与 IDC 网络可选。
            在线选购、自助管理，按规格计费，让业务快速上线。
          </p>
          <div class="trust-row">
            <span>BGP 多线接入</span><i></i>
            <span>NVMe SSD 存储</span><i></i>
            <span>DDoS 基础防护</span><i></i>
            <span>99.9% SLA</span><i></i>
            <span>7×24 技术支持</span>
          </div>
          <el-button type="primary" @click="$router.push('/')">立即选购</el-button>
        </section>

        <section id="features" class="info-block">
          <h2>核心能力</h2>
          <p class="lead">从云主机到公网对接，一站式满足部署、跨境、回源等场景。</p>
          <div class="card-grid">
            <div v-for="f in features" :key="f.title" class="info-card">
              <div class="info-icon" :style="{ background: f.bg }">
                <el-icon :size="20"><component :is="f.icon" /></el-icon>
              </div>
              <h3>{{ f.title }}</h3>
              <p>{{ f.desc }}</p>
            </div>
          </div>
        </section>

        <section id="scenarios" class="info-block">
          <h2>适用场景</h2>
          <p class="lead">按实际业务匹配合适的资源，从稳定算力到跨境链路。</p>
          <div class="scene-list">
            <button v-for="item in scenarios" :key="item.title" type="button" class="scene-card" @click="goBuy(item.category)">
              <span class="info-icon"><el-icon><component :is="item.icon" /></el-icon></span>
              <span><b>{{ item.title }}</b><small>{{ item.desc }}</small></span>
            </button>
          </div>
        </section>

        <section id="delivery" class="info-block">
          <h2>透明交付</h2>
          <p class="lead">从选购到管理，流程清晰可追踪。</p>
          <div class="step-grid">
            <div v-for="(item, index) in deliverySteps" :key="item.title" class="step-card">
              <span class="step-no">0{{ index + 1 }}</span>
              <h3>{{ item.title }}</h3>
              <p>{{ item.desc }}</p>
            </div>
          </div>
        </section>

        <section id="why" class="info-block">
          <h2>为什么选择我们</h2>
          <ul class="why-list">
            <li v-for="w in whyList" :key="w">
              <el-icon color="#10b981"><CircleCheckFilled /></el-icon>{{ w }}
            </li>
          </ul>
          <div class="panel">
            <div v-for="r in panelRows" :key="r.k" class="panel-row">
              <span>{{ r.k }}</span><b>{{ r.v }}</b>
            </div>
          </div>
        </section>
      </article>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const features = [
  { title: 'VPS 云主机', desc: '独立 vCPU / 内存 / NVMe 硬盘，多种规格按需选配，支持升降配。', icon: 'Cpu', bg: '#eff6ff' },
  { title: '公网对接', desc: '购买后由客户自行选择 GRE 或 WireGuard 对接，优化跨境与回源链路。', icon: 'Connection', bg: '#ecfeff' },
  { title: '原生 / 广播 IP', desc: '原生 IP 解锁流媒体，广播 IP 灵活调度，满足多样合规需求。', icon: 'Promotion', bg: '#f5f3ff' },
  { title: '家宽 / IDC 网络', desc: '家宽与 IDC 网络类型可选，匹配采集、加速、托管等不同业务。', icon: 'Histogram', bg: '#fef2f2' },
  { title: '自助控制台', desc: '服务、订单、账单、资源一目了然，配置变更在线提交。', icon: 'Monitor', bg: '#f0fdf4' },
  { title: '透明计费', desc: '基础规格 + 超出阶梯计费，多币种在线支付，账单逐项可查。', icon: 'Wallet', bg: '#fffbeb' },
]
const scenarios = [
  { title: '业务应用部署', desc: '为网站、应用和服务提供稳定的 VPS 算力资源。', icon: 'Cpu', category: 'vps' },
  { title: '跨境访问加速', desc: '通过公网对接资源优化网络链路与回源体验。', icon: 'Connection', category: 'edge' },
  { title: '资源弹性扩展', desc: '根据 CPU、内存、带宽和 IP 等需求灵活选配。', icon: 'DataAnalysis', category: '' },
]
const deliverySteps = [
  { title: '选择产品', desc: '按区域、网络类型与 IP 属性筛选合适资源。' },
  { title: '提交订单', desc: '确认配置与需求后，系统生成可跟踪的服务工单。' },
  { title: '控制台管理', desc: '在统一控制台查看服务、资源状态与账单明细。' },
]
const whyList = [
  '覆盖亚太 / 北美 / 欧洲等多大区节点',
  '原生 IP、广播 IP、家宽、IDC 多维度可选',
  '产品化定价：基础规格 + 超出部分阶梯计费',
  '下单到开通全流程可在控制台跟踪',
  '账单逐项透明，支持多币种在线结算',
]
const panelRows = [
  { k: '节点区域', v: '亚太 / 北美 / 欧洲' },
  { k: '网络类型', v: 'IDC · 家宽' },
  { k: 'IP 属性', v: '原生 · 广播' },
  { k: '对接协议', v: 'GRE · WireGuard' },
  { k: '计费方式', v: '月租 + 超出阶梯' },
]

function go(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  router.replace({ hash: `#${id}` })
}
function goBuy(category) {
  router.push({ name: 'products', query: category ? { category } : {} })
}

function scrollHash() {
  const id = (route.hash || '').replace('#', '')
  if (id) nextTick(() => document.getElementById(id)?.scrollIntoView({ block: 'start' }))
}
onMounted(scrollHash)
watch(() => route.hash, scrollHash)
</script>

<style scoped>
.info-page { background: #f5f5f5; padding: 20px 0 48px; }
.info-wrap {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 20px;
  align-items: start;
}
.info-nav {
  position: sticky;
  top: 72px;
  padding: 16px;
  background: #fff;
  border: 1px solid var(--ce-border);
  border-radius: 10px;
}
.info-nav h3 { margin: 0 0 12px; font-size: 14px; }
.info-nav a {
  display: block;
  padding: 8px 0;
  color: var(--ce-text-secondary);
  font-size: 13px;
}
.info-nav a:hover { color: var(--ce-primary); }
.info-main {
  background: #fff;
  border: 1px solid var(--ce-border);
  border-radius: 10px;
  padding: 28px 32px 36px;
}
.info-block { padding-top: 8px; margin-bottom: 36px; scroll-margin-top: 76px; }
.info-block:last-child { margin-bottom: 0; }
h1 { margin: 6px 0 12px; font-size: 28px; }
h2 { margin: 0 0 8px; font-size: 20px; }
.lead, .info-block > p { color: var(--ce-muted); line-height: 1.7; margin: 0 0 16px; }
.trust-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  align-items: center;
  color: var(--ce-muted);
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 18px;
}
.trust-row i { width: 4px; height: 4px; border-radius: 50%; background: var(--ce-border); }
.card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.info-card, .step-card, .scene-card {
  padding: 16px;
  border: 1px solid var(--ce-border);
  border-radius: 10px;
  background: #fff;
}
.info-card h3, .step-card h3 { margin: 0 0 6px; font-size: 15px; }
.info-card p, .step-card p { margin: 0; color: var(--ce-muted); font-size: 13px; line-height: 1.6; }
.info-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--ce-primary);
  background: var(--ce-primary-soft);
  margin-bottom: 10px;
}
.scene-list { display: grid; gap: 10px; }
.scene-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  text-align: left;
  cursor: pointer;
}
.scene-card:hover { border-color: #bfdbfe; }
.scene-card b { display: block; font-size: 14px; }
.scene-card small { color: var(--ce-muted); font-size: 12px; }
.step-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.step-no { color: var(--ce-primary); font-size: 12px; font-weight: 800; }
.why-list { list-style: none; padding: 0; margin: 0 0 16px; }
.why-list li { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; font-size: 14px; }
.panel {
  border: 1px solid var(--ce-border);
  border-radius: 10px;
  padding: 4px 16px;
  background: var(--ce-surface-subtle);
}
.panel-row {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--ce-border);
  color: var(--ce-muted);
  font-size: 14px;
}
.panel-row:last-child { border-bottom: none; }
.panel-row b { color: var(--ce-text); }
@media (max-width: 860px) {
  .info-wrap { grid-template-columns: 1fr; }
  .info-nav { position: static; display: flex; flex-wrap: wrap; gap: 8px 14px; }
  .info-nav h3 { width: 100%; }
  .card-grid, .step-grid { grid-template-columns: 1fr; }
}
</style>
