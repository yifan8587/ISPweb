<template>
  <div class="info-page">
    <div class="ce-container ce-container--wide info-wrap">
      <aside class="info-nav">
        <h3>使用帮助</h3>
        <a href="#buy" @click.prevent="go('buy')">如何选购</a>
        <a href="#order" @click.prevent="go('order')">下单与开通</a>
        <a href="#protocol" @click.prevent="go('protocol')">公网对接协议</a>
        <a href="#account" @click.prevent="go('account')">系统与账号</a>
        <a href="#nat" @click.prevent="go('nat')">NAT IP 说明</a>
        <a href="#manage" @click.prevent="go('manage')">服务管理</a>
        <a href="#faq" @click.prevent="go('faq')">常见问题</a>
      </aside>

      <article class="info-main">
        <section id="buy" class="info-block">
          <span class="ce-eyebrow">使用帮助</span>
          <h1>如何选购</h1>
          <p>
            打开首页即可浏览全部在线产品。可按产品类别（VPS / 公网对接）、网络类型（IDC / 家宽）、
            IP 属性、地区进行筛选，也可按价格排序。
          </p>
          <ol>
            <li>在首页选择 <b>VPS</b> 或 <b>公网对接</b>。</li>
            <li>按网络类型、IP 属性、区域缩小范围。</li>
            <li>点击产品卡片查看规格并下单。</li>
          </ol>
          <el-button type="primary" @click="$router.push('/')">去选购</el-button>
        </section>

        <section id="order" class="info-block">
          <h2>下单与开通</h2>
          <ol>
            <li>确认规格、数量与支付方式后提交订单。</li>
            <li>完成支付即可离开。库存充足时系统在后台开通；库存不足时订单保持待交付，并通知管理员。</li>
            <li>管理员补齐资源并手动交付后，可在控制台「我的订单」查看交付状态，并在「我的服务」中管理。</li>
          </ol>
          <p>库存不足时仍可下单。支付完成后不会自动开通，交付状态以「我的订单」为准。</p>
        </section>

        <section id="protocol" class="info-block">
          <h2>公网对接协议</h2>
          <p>
            公网对接产品本身不绑定 GRE 或 WireGuard。下单时请在详情页选择对接协议，
            开通后也可在控制台按对端情况补全隧道参数。
          </p>
          <ul>
            <li><b>GRE</b>：适合已有公网固定 IP 的对端。</li>
            <li><b>WireGuard</b>：适合需要密钥认证的隧道。</li>
          </ul>
        </section>

        <section id="account" class="info-block">
          <h2>系统与账号</h2>
          <p>
            VPS 开通时请选择操作系统版本。登录账号统一为 <b>root</b>，
            密码在下单时设置或由系统生成。
          </p>
        </section>

        <section id="nat" class="info-block">
          <h2>NAT IP 说明</h2>
          <p>
            部分公网对接产品的业务 IP 为 NAT 交付，产品卡片会在规格后标注 <b>NAT IP</b>。
            此类地址不能公网直连，需按控制台提供的网关与掩码配置，经节点 NAT 访问。
          </p>
        </section>

        <section id="manage" class="info-block">
          <h2>服务管理</h2>
          <p>登录控制台后可查看服务、订单、账单与资源，并提交变更或工单。</p>
          <el-button @click="$router.push('/console')">进入控制台</el-button>
        </section>

        <section id="faq" class="info-block">
          <h2>常见问题</h2>
          <el-collapse class="faq-list">
            <el-collapse-item v-for="item in faqs" :key="item.q" :title="item.q">
              <p>{{ item.a }}</p>
            </el-collapse-item>
          </el-collapse>
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

const faqs = [
  { q: '如何选择适合的产品？', a: '可按区域、网络类型、IP 属性与基础规格筛选；详情页支持查看配置与可选升级项。' },
  { q: '下单后如何查看进度？', a: '订单提交后会生成服务工单，您可在控制台的订单与服务页面查看处理状态。' },
  { q: '是否可以变更已开通的服务？', a: '可通过服务管理功能提交变更需求，具体以产品可支持的规格与审核结果为准。' },
  { q: '公网对接必须选 GRE 还是 WireGuard？', a: '产品不预绑定协议。请在详情页自行选择，开通后再按对端补全参数。' },
  { q: 'VPS 默认登录账号是什么？', a: '统一使用 root 账号，密码以您下单时填写或系统生成为准。' },
]

function go(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  router.replace({ hash: `#${id}` })
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
.info-block { padding-top: 8px; margin-bottom: 32px; scroll-margin-top: 76px; }
.info-block:last-child { margin-bottom: 0; }
h1 { margin: 6px 0 12px; font-size: 28px; }
h2 { margin: 0 0 10px; font-size: 20px; }
p, li { color: var(--ce-text-secondary); line-height: 1.75; }
.info-block > p { margin: 0 0 14px; }
ol, ul { margin: 0 0 16px; padding-left: 18px; }
.faq-list { border-top: 1px solid var(--ce-border); }
.faq-list :deep(.el-collapse-item__header) { height: 52px; font-weight: 650; }
.faq-list p { margin: 0 0 14px; }
@media (max-width: 860px) {
  .info-wrap { grid-template-columns: 1fr; }
  .info-nav { position: static; display: flex; flex-wrap: wrap; gap: 8px 14px; }
  .info-nav h3 { width: 100%; }
}
</style>
