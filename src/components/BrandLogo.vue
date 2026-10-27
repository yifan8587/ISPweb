<template>
  <img
    class="brand-logo"
    :class="[`is-${size}`, { 'is-icon': icon }]"
    :src="logoSrc"
    alt="十极 10G.HK"
  />
</template>

<script setup>
import logoSrc from '@/assets/logo.webp'

defineProps({
  size: { type: String, default: 'nav' },
  icon: { type: Boolean, default: false },
})
</script>

<style scoped>
.brand-logo {
  display: block;
  width: auto;
  height: 54px;
  object-fit: contain;
  object-position: left center;
  border-radius: 8px;
  background: transparent;
}
.is-nav { height: 54px; }
.is-footer { height: 64px; }
.is-auth { height: 80px; }
.is-console { height: 40px; max-width: 168px; }
.is-icon {
  width: 36px;
  height: 36px;
  max-width: 36px;
  object-fit: cover;
  object-position: 22% center;
}
@media (max-width: 640px) {
  .is-nav { height: 40px; }
  .is-footer { height: 48px; }
  .is-auth { height: 56px; }
}
</style>
