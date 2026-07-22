<template>
  <BrandScenicLogo />
  <SideRailTabs />
  <RouterView />
  <ClickEffects />
</template>

<script setup>
import BrandScenicLogo from './components/BrandScenicLogo.vue'
import ClickEffects from './components/ClickEffects.vue'
import SideRailTabs from './components/SideRailTabs.vue'
</script>
