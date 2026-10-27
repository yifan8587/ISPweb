<template>
  <div class="public-layout">
    <header class="nav" :class="{ scrolled }">
      <div class="ce-container ce-container--wide nav-inner">
        <router-link to="/" class="brand" aria-label="十极 10G.HK 首页" title="十极 10G.HK">
          <BrandLogo size="nav" />
        </router-link>

        <nav class="nav-links" :class="{ open: menuOpen }" @click="menuOpen = false">
          <router-link to="/" exact-active-class="active">首页</router-link>
          <router-link to="/products" active-class="active">全部产品</router-link>
          <router-link v-if="auth.isLoggedIn" to="/console" class="nav-console-link">控制台</router-link>
        </nav>

        <div class="nav-actions">
          <template v-if="auth.isLoggedIn">
            <el-button class="console-entry" text @click="$router.push('/console')">控制台</el-button>
            <el-dropdown @command="onCommand">
              <span class="user-chip">
                <el-icon><User /></el-icon>
                <span class="user-name">{{ auth.displayName }}</span>
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="console">进入控制台</el-dropdown-item>
                  <el-dropdown-item command="profile">账户资料</el-dropdown-item>
                  <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <el-button text @click="$router.push('/login')">登录</el-button>
            <el-button type="primary" @click="$router.push('/register')">注册</el-button>
          </template>
        </div>
        <button
          type="button"
          class="nav-toggle"
          :aria-expanded="menuOpen"
          aria-label="打开导航菜单"
          @click="menuOpen = !menuOpen"
        >
          <el-icon><component :is="menuOpen ? 'Close' : 'Menu'" /></el-icon>
        </button>
      </div>
    </header>

    <main class="public-main">
      <router-view />
    </main>

    <footer class="footer">
      <div class="ce-container ce-container--wide footer-inner">
        <div class="footer-brand">
          <div class="brand">
            <BrandLogo size="footer" />
          </div>
          <p>全球 VPS 主机与公网对接服务，在线选购、自助管理。</p>
        </div>
        <div class="footer-col">
          <h4>产品</h4>
          <router-link to="/products?category=vps">VPS 云主机</router-link>
          <router-link to="/products?category=edge">公网对接</router-link>
          <router-link to="/products">全部产品</router-link>
        </div>
        <div class="footer-col">
          <h4>产品介绍</h4>
          <router-link to="/about">平台简介</router-link>
          <router-link to="/about#features">核心能力</router-link>
          <router-link to="/about#scenarios">适用场景</router-link>
          <router-link to="/about#delivery">透明交付</router-link>
          <router-link to="/about#why">为什么选择我们</router-link>
        </div>
        <div class="footer-col">
          <h4>使用帮助</h4>
          <router-link to="/help">如何选购</router-link>
          <router-link to="/help#order">下单与开通</router-link>
          <router-link to="/help#protocol">公网对接协议</router-link>
          <router-link to="/help#nat">NAT IP 说明</router-link>
          <router-link to="/help#faq">常见问题</router-link>
        </div>
        <div class="footer-col">
          <h4>账户</h4>
          <router-link to="/login">登录</router-link>
          <router-link to="/register">注册</router-link>
          <router-link to="/console">控制台</router-link>
        </div>
      </div>
      <div class="footer-bottom">
        <div class="ce-container ce-container--wide">
          © {{ year }} 10g.hk · Powered by ISPmanager
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import BrandLogo from '@/components/BrandLogo.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const scrolled = ref(false)
const menuOpen = ref(false)
const year = new Date().getFullYear()

watch(() => route.fullPath, () => {
  menuOpen.value = false
})

function onScroll() {
  scrolled.value = window.scrollY > 8
}
function onCommand(cmd) {
  if (cmd === 'console') router.push('/console')
  else if (cmd === 'profile') router.push('/console/profile')
  else if (cmd === 'logout') {
    auth.logout()
    router.push('/')
  }
}

onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped>
.public-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: #fff;
  border-bottom: 1px solid var(--ce-border);
}
.nav.scrolled {
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
}
.nav-inner {
  height: 68px;
  display: flex;
  align-items: center;
  gap: 28px;
}
.brand {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
}
.nav-links {
  display: flex;
  gap: 22px;
  flex: 1;
}
.nav-links a {
  font-size: 14px;
  font-weight: 600;
  color: var(--ce-text-secondary);
}
.nav-links a:hover,
.nav-links a.active { color: var(--ce-primary); }
.nav-toggle {
  display: none;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--ce-text);
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.nav-toggle:hover { background: var(--ce-primary-soft); }
.nav-console-link { display: none; }
.nav-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
}
.user-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-weight: 650;
  color: var(--ce-text-secondary);
  padding: 6px 10px;
  border-radius: 8px;
  max-width: 220px;
}
.user-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-chip:hover { background: var(--ce-primary-soft); }
.public-main { flex: 1; }
.footer {
  background: #0a1222;
  color: #cbd5e1;
  margin-top: 0;
}
.footer-inner {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr 1fr 1fr;
  gap: 28px 24px;
  padding-top: 36px;
  padding-bottom: 28px;
}
.footer-brand p {
  margin: 12px 0 0;
  max-width: 260px;
  line-height: 1.6;
  color: #94a3b8;
  font-size: 13px;
}
.footer-col h4 {
  color: #fff;
  font-size: 14px;
  margin: 0 0 12px;
}
.footer-col a {
  display: block;
  color: #94a3b8;
  font-size: 13px;
  margin-bottom: 10px;
}
.footer-col a:hover { color: #fff; }
.footer-bottom {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 12px 0;
  font-size: 12px;
  color: #64748b;
}
@media (max-width: 860px) {
  .footer-inner { grid-template-columns: 1fr 1fr; }
  .nav-inner { gap: 16px; }
}
@media (max-width: 720px) {
  .nav-inner { height: 56px; gap: 8px; }
  .nav-toggle { display: inline-flex; }
  .nav-links {
    display: none;
    position: absolute;
    left: 0;
    right: 0;
    top: 56px;
    flex-direction: column;
    gap: 2px;
    padding: 8px 12px 12px;
    background: #fff;
    border-bottom: 1px solid var(--ce-border);
    box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
  }
  .nav-links.open { display: flex; }
  .nav-links a { padding: 12px 8px; border-radius: 8px; }
  .nav-console-link { display: block; }
  .console-entry { display: none; }
  .user-chip { max-width: 120px; padding: 6px; }
  .footer-inner { grid-template-columns: 1fr; }
}
</style>
