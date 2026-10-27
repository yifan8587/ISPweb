<template>
  <div class="console" :class="{ 'is-collapsed': isSidebarCollapsed }">
    <aside id="console-sidebar" class="sidebar" :class="{ 'mobile-open': isMobileMenuOpen }" aria-label="控制台主导航">
      <div class="sidebar-head">
        <router-link to="/" class="brand" aria-label="十极 10G.HK 首页" title="十极 10G.HK" @click="closeMobileMenu">
          <BrandLogo size="console" :icon="isSidebarCollapsed && !isMobile" />
        </router-link>
        <button
          class="sidebar-toggle"
          type="button"
          :aria-label="isSidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'"
          :aria-expanded="!isSidebarCollapsed"
          :title="isSidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'"
          @click="toggleSidebar"
        >
          <el-icon><component :is="isSidebarCollapsed ? Expand : Fold" /></el-icon>
        </button>
      </div>

      <nav class="menu" aria-label="控制台功能导航">
        <router-link
          v-for="m in menus"
          :key="m.name"
          :to="{ name: m.name }"
          class="menu-item"
          active-class="active"
          :aria-label="m.label"
          :title="isSidebarCollapsed ? m.label : undefined"
          @click="closeMobileMenu"
        >
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-foot">
        <router-link to="/products" class="buy-btn" aria-label="选购新服务" title="选购新服务" @click="closeMobileMenu">
          <el-icon><Plus /></el-icon>
          <span class="buy-label">选购新服务</span>
        </router-link>
      </div>
    </aside>
    <button
      v-if="isMobileMenuOpen"
      class="sidebar-overlay"
      type="button"
      aria-label="关闭导航菜单"
      title="关闭导航菜单"
      @click="closeMobileMenu"
    />

    <div class="main-area">
      <header class="topbar">
        <div class="crumb">
          <button
            class="mobile-menu-toggle"
            type="button"
            aria-controls="console-sidebar"
            :aria-expanded="isMobileMenuOpen"
            :aria-label="isMobileMenuOpen ? '关闭导航菜单' : '打开导航菜单'"
            :title="isMobileMenuOpen ? '关闭导航菜单' : '打开导航菜单'"
            @click="toggleMobileMenu"
          >
            <el-icon><component :is="isMobileMenuOpen ? Close : Menu" /></el-icon>
          </button>
          <el-icon><component :is="currentMenu?.icon || 'Odometer'" /></el-icon>
          {{ currentMenu?.label || '控制台' }}
        </div>
        <div class="top-actions">
          <router-link to="/" class="back-site">返回官网</router-link>
          <el-dropdown @command="onCommand">
            <span class="user-chip">
              <el-avatar :size="28" style="background:var(--ce-primary)">{{ initial }}</el-avatar>
              {{ auth.displayName }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">账户资料</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <section class="content">
        <div class="content-scroll">
          <el-alert
            v-if="waitingAdmin.length"
            class="provision-alert"
            type="warning"
            :closable="false"
            show-icon
            :title="waitingTitle"
          >
            <template #default>
              <el-button link type="primary" @click="$router.push({ name: 'orders' })">查看交付状态</el-button>
            </template>
          </el-alert>
          <el-alert
            v-if="opening.length"
            class="provision-alert"
            type="info"
            :closable="false"
            show-icon
            :title="provisioningTitle"
          />
          <el-alert
            v-if="ready.length"
            class="provision-alert"
            type="success"
            :closable="false"
            show-icon
          >
            <template #title>
              {{ readyTitle }}
              <el-button link type="primary" @click="$router.push({ name: 'services' })">去管理</el-button>
            </template>
          </el-alert>
          <router-view />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { Close, Expand, Fold, Menu } from '@element-plus/icons-vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { useProvisionNotices } from '@/composables/useProvisionNotices'
import BrandLogo from '@/components/BrandLogo.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const isSidebarCollapsed = ref(false)
const isMobileMenuOpen = ref(false)
const isMobile = ref(false)
const sidebarStorageKey = 'ispweb.console.sidebar-collapsed'
let mobileMediaQuery

const menus = [
  { name: 'dashboard', label: '总览', icon: 'Odometer' },
  { name: 'services', label: '我的服务', icon: 'Connection' },
  { name: 'resources', label: '资源管理', icon: 'Cpu' },
  { name: 'orders', label: '我的订单', icon: 'Document' },
  { name: 'inquiries', label: '我的咨询', icon: 'ChatDotRound' },
  { name: 'tickets', label: '技术工单', icon: 'Ticket' },
  { name: 'bills', label: '账单中心', icon: 'Wallet' },
  { name: 'profile', label: '账户资料', icon: 'User' },
]

const currentMenu = computed(() => menus.find((m) => m.name === route.name))
const initial = computed(() => (auth.displayName || 'U').charAt(0).toUpperCase())
const { provisioning, ready } = useProvisionNotices()
const waitingAdmin = computed(() => provisioning.value.filter((item) => item.waiting_admin || item.status === 'insufficient'))
const opening = computed(() => provisioning.value.filter((item) => !(item.waiting_admin || item.status === 'insufficient')))
const waitingTitle = computed(() => {
  const first = waitingAdmin.value[0]
  if (!first) return ''
  if (waitingAdmin.value.length === 1) {
    return `${first.product_name || first.order_no} 已付款，库存不足，等待管理员交付`
  }
  return `有 ${waitingAdmin.value.length} 笔订单已付款，等待管理员补齐资源后手动交付`
})
const provisioningTitle = computed(() => {
  const first = opening.value[0]
  if (!first) return ''
  if (opening.value.length === 1) {
    return `${first.product_name || first.order_no} 正在开通，完成后可在「我的服务」管理`
  }
  return `有 ${opening.value.length} 笔服务正在开通，完成后可在「我的服务」管理`
})
const readyTitle = computed(() => {
  const first = ready.value[0]
  if (!first) return ''
  if (ready.value.length === 1) {
    return `${first.product_name || first.instance_no} 已开通`
  }
  return `有 ${ready.value.length} 个服务已开通`
})

function toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
  localStorage.setItem(sidebarStorageKey, String(isSidebarCollapsed.value))
}

function closeMobileMenu() {
  isMobileMenuOpen.value = false
}

function toggleMobileMenu() {
  if (isMobile.value) isMobileMenuOpen.value = !isMobileMenuOpen.value
}

function handleMobileChange(event) {
  isMobile.value = event.matches
  if (!event.matches) closeMobileMenu()
}

function onCommand(cmd) {
  if (cmd === 'profile') router.push({ name: 'profile' })
  else if (cmd === 'logout') {
    auth.logout()
    router.push('/')
  }
}

onMounted(() => {
  isSidebarCollapsed.value = localStorage.getItem(sidebarStorageKey) === 'true'
  mobileMediaQuery = window.matchMedia('(max-width: 860px)')
  handleMobileChange(mobileMediaQuery)
  mobileMediaQuery.addEventListener('change', handleMobileChange)
})

onBeforeUnmount(() => {
  mobileMediaQuery?.removeEventListener('change', handleMobileChange)
})
</script>

<style scoped>
.console {
  --sidebar-expanded-width: 244px;
  --sidebar-collapsed-width: 72px;
  --sidebar-width: var(--sidebar-expanded-width);
  min-height: 100vh;
  width: 100%;
  display: flex;
  background: var(--ce-bg);
  overflow-x: hidden;
}
.console.is-collapsed {
  --sidebar-width: var(--sidebar-collapsed-width);
}
.sidebar {
  width: var(--sidebar-width);
  background: var(--ce-dark);
  color: #cbd5e1;
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  z-index: 30;
  overflow-x: hidden;
  transition: width 0.2s ease, transform 0.2s ease;
}
.sidebar-head {
  display: flex;
  align-items: center;
  min-height: 68px;
  padding: 0 12px 0 22px;
}
.sidebar .brand {
  display: flex;
  align-items: center;
  min-width: 0;
  overflow: hidden;
}
.sidebar-toggle,
.mobile-menu-toggle,
.sidebar-overlay {
  border: 0;
  font: inherit;
  cursor: pointer;
}
.sidebar-toggle {
  width: 36px;
  height: 36px;
  margin-left: auto;
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
}
.sidebar-toggle:hover,
.sidebar-toggle:focus-visible {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  outline: none;
}
.menu {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 12px;
}
.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  border-radius: 10px;
  color: #94a3b8;
  font-weight: 500;
  font-size: 15px;
  transition: all 0.18s;
}
.menu-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}
.menu-item.active {
  background: linear-gradient(120deg, var(--ce-primary), #3b82f6);
  color: #fff;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.4);
}
.console.is-collapsed .sidebar-head {
  padding: 0 12px;
}
.console.is-collapsed .sidebar .brand {
  width: 36px;
  justify-content: center;
}
.console.is-collapsed .menu-item span,
.console.is-collapsed .buy-label {
  display: none;
}
.console.is-collapsed .menu {
  padding: 0 10px;
}
.console.is-collapsed .menu-item {
  justify-content: center;
  padding: 11px;
}
.console.is-collapsed .sidebar-foot {
  padding: 16px 10px;
}
.console.is-collapsed .buy-btn {
  padding: 11px;
}
.sidebar-foot {
  margin-top: auto;
  padding: 16px;
}
.buy-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px dashed rgba(255, 255, 255, 0.25);
  color: #e2e8f0;
  padding: 11px;
  border-radius: 10px;
  font-weight: 600;
  transition: all 0.2s;
}
.buy-btn:hover {
  background: rgba(96, 165, 250, 0.18);
  border-color: #60a5fa;
  color: #fff;
}
.main-area {
  flex: 1;
  min-width: 0;
  margin-left: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  transition: margin-left 0.2s ease;
}
.topbar {
  min-width: 0;
  height: 64px;
  background: #fff;
  border-bottom: 1px solid var(--ce-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  position: sticky;
  top: 0;
  z-index: 10;
}
.crumb {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-weight: 700;
  font-size: 17px;
}
.mobile-menu-toggle {
  display: none;
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 8px;
  background: var(--ce-surface-subtle);
  color: var(--ce-text);
}
.mobile-menu-toggle:hover,
.mobile-menu-toggle:focus-visible {
  background: var(--ce-primary-soft);
  color: var(--ce-primary);
  outline: none;
}
.top-actions {
  display: flex;
  align-items: center;
  gap: 18px;
}
.back-site {
  color: var(--ce-muted);
  font-size: 14px;
}
.back-site:hover {
  color: var(--ce-primary);
}
.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 600;
}
.content {
  min-width: 0;
  flex: 1;
  padding: 28px;
  overflow-x: auto;
}
@media (min-width: 1600px) {
  .content { padding: 28px 24px; }
}
@media (max-width: 1100px) {
  .content { padding: 22px 18px; }
  .topbar { padding: 0 18px; }
}
.content-scroll {
  min-width: 0;
}
.provision-alert {
  margin-bottom: 14px;
}
@media (max-width: 860px) {
  .console,
  .console.is-collapsed {
    --sidebar-width: 0px;
  }
  .sidebar {
    width: min(280px, calc(100vw - 44px));
    transform: translateX(-100%);
    box-shadow: none;
  }
  .sidebar.mobile-open {
    transform: translateX(0);
    box-shadow: var(--ce-shadow-lg);
  }
  .sidebar-overlay {
    position: fixed;
    z-index: 20;
    inset: 0;
    width: 100%;
    height: 100%;
    background: rgba(15, 23, 42, 0.48);
  }
  .console.is-collapsed .sidebar-head {
    padding: 0 12px 0 22px;
  }
  .console.is-collapsed .sidebar .brand {
    width: auto;
    justify-content: flex-start;
  }
  .console.is-collapsed .menu-item span,
  .console.is-collapsed .buy-label {
    display: inline;
  }
  .console.is-collapsed .menu {
    padding: 0 12px;
  }
  .console.is-collapsed .menu-item {
    justify-content: flex-start;
    padding: 11px 14px;
  }
  .console.is-collapsed .sidebar-foot {
    padding: 16px;
  }
  .console.is-collapsed .buy-btn {
    padding: 11px;
  }
  .sidebar-toggle {
    display: none;
  }
  .main-area {
    margin-left: 0;
  }
  .mobile-menu-toggle {
    display: grid;
  }
  .topbar {
    padding: 0 16px;
  }
  .content {
    padding: 18px 16px;
  }
  .top-actions {
    gap: 10px;
  }
  .back-site {
    display: none;
  }
}
@media (max-width: 480px) {
  .user-chip {
    gap: 0;
  }
  .user-chip > :not(.el-avatar) {
    display: none;
  }
}
</style>
