<script setup>
import { RefreshCw } from 'lucide-vue-next'

defineProps({ state: { type: Object, required: true } })
defineEmits(['retry'])
</script>

<template>
  <div class="async-block">
    <div v-if="state.loading" class="skeleton">
      <span></span><span></span><span></span>
    </div>
    <div v-else-if="state.error" class="empty-panel error">
      <strong>{{ state.error }}</strong>
      <button class="text-button" @click="$emit('retry')"><RefreshCw />重试</button>
    </div>
    <slot v-else-if="state.data" :data="state.data" />
    <div v-else class="empty-panel">暂无数据</div>
  </div>
</template>

<style scoped>
.skeleton {
  display: grid;
  gap: 10px;
  padding: 22px;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--surface);
}
.skeleton span {
  height: 18px;
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, var(--surface-soft), var(--surface-pressed), var(--surface-soft));
  background-size: 220% 100%;
  animation: load 1.2s ease-out infinite;
}
.skeleton span:nth-child(2) { width: 74%; }
.skeleton span:nth-child(3) { width: 52%; }
.empty-panel {
  display: flex;
  min-height: 160px;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--surface);
  color: var(--muted);
}
.error {
  flex-direction: column;
  color: var(--rise);
}
@keyframes load {
  from { background-position: 100% 0; }
  to { background-position: -100% 0; }
}
</style>
