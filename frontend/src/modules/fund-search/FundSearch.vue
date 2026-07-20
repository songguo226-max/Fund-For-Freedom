<script setup>
import { ArrowRight, LoaderCircle, Search, X } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../integrations/fund-api'
import { resolveFundTarget } from './fundSearchResolve'

const router = useRouter()
const query = ref('')
const hits = ref([])
const loading = ref(false)
const error = ref('')
let timer = null

const canSubmit = computed(() => query.value.trim().length >= 2)

watch(query, (value) => {
  clearTimeout(timer)
  hits.value = []
  error.value = ''
  const q = value.trim()
  if (q.length < 2) return
  timer = setTimeout(async () => {
    loading.value = true
    try {
      hits.value = await api.search(q)
    } catch (err) {
      error.value = err.message || '搜索失败'
    } finally {
      loading.value = false
    }
  }, 260)
})

async function submit() {
  const q = query.value.trim()
  if (!q) return
  clearTimeout(timer)

  let target = resolveFundTarget(q, hits.value)
  if (!target) {
    loading.value = true
    error.value = ''
    try {
      hits.value = await api.search(q)
      target = resolveFundTarget(q, hits.value)
    } catch (err) {
      error.value = err.message || '搜索失败'
    } finally {
      loading.value = false
    }
  }

  if (!target) {
    error.value = '未找到匹配的基金'
    return
  }
  router.push(`/fund/${encodeURIComponent(target)}`)
}

function go(code) {
  const target = resolveFundTarget(code, hits.value)
  if (!target) return
  router.push(`/fund/${encodeURIComponent(target)}`)
}

function clear() {
  query.value = ''
  hits.value = []
}
</script>

<template>
  <form class="search-box" aria-label="基金查询" @submit.prevent="submit">
    <span class="search-symbol" aria-hidden="true">
      <Search class="search-icon" />
    </span>
    <input
      v-model="query"
      class="search-input"
      name="fund-search"
      placeholder="输入基金代码或名称"
      autocomplete="off"
      aria-label="输入基金代码或名称"
    />
    <button v-if="query" class="icon-button clear" type="button" title="清空" @click="clear">
      <X />
    </button>
    <button class="primary-button submit" type="submit" :disabled="!canSubmit">查询<ArrowRight /></button>
    <div v-if="hits.length || loading || error" class="suggestions">
      <div v-if="loading" class="suggestion muted"><LoaderCircle class="spin" />搜索中</div>
      <button v-for="hit in hits" :key="hit.code" type="button" class="suggestion" @click="go(hit.code)">
        <span>
          <strong>{{ hit.name }}</strong>
          <small>{{ hit.type || '基金' }}</small>
        </span>
        <b>{{ hit.code }}<ArrowRight /></b>
      </button>
      <div v-if="error" class="suggestion err">{{ error }}</div>
    </div>
  </form>
</template>

<style scoped>
.search-box {
  position: relative;
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto auto;
  align-items: center;
  min-height: 60px;
  padding: 6px;
  border: 1px solid oklch(87.8% 0.014 250);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: 0 8px 22px rgba(30, 39, 52, 0.045), inset 0 1px 0 oklch(100% 0 0 / 0.7);
  transition: border-color 170ms cubic-bezier(0.19, 1, 0.22, 1), box-shadow 170ms cubic-bezier(0.19, 1, 0.22, 1), background 170ms cubic-bezier(0.19, 1, 0.22, 1);
}
.search-box:hover {
  border-color: var(--line-strong);
  box-shadow: 0 10px 24px rgba(30, 39, 52, 0.055), inset 0 1px 0 oklch(100% 0 0 / 0.72);
}
.search-box:focus-within {
  border-color: oklch(61% 0.095 255);
  box-shadow: 0 10px 24px rgba(30, 39, 52, 0.06), 0 0 0 3px oklch(92.8% 0.03 255), inset 0 1px 0 oklch(100% 0 0 / 0.74);
}
.search-symbol {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  color: oklch(55% 0.02 250);
  pointer-events: none;
  transition: color 170ms cubic-bezier(0.19, 1, 0.22, 1);
}
.search-box:focus-within .search-symbol {
  color: oklch(44% 0.11 255);
}
.search-icon {
  width: 21px;
  height: 21px;
  stroke-width: 1.85;
}
.search-input {
  width: 100%;
  min-width: 0;
  height: 46px;
  padding: 0 10px 0 0;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--text);
  font-size: 16px;
  letter-spacing: 0;
}
.search-input::placeholder {
  color: oklch(66% 0.018 250);
}
.clear {
  width: 34px;
  min-height: 34px;
  margin-right: 8px;
  border-color: transparent;
  background: transparent;
  color: var(--muted);
}
.clear:hover {
  border-color: var(--line);
  background: var(--surface-soft);
  color: var(--text);
}
.submit {
  min-width: 86px;
  height: 40px;
  margin-right: 0;
  padding: 0 14px 0 16px;
  border-color: oklch(42% 0.13 255);
  background: var(--accent);
  color: oklch(98.5% 0.004 250);
  box-shadow: 0 7px 16px rgba(37, 85, 156, 0.16), inset 0 1px 0 oklch(100% 0 0 / 0.22);
  transition: background 170ms cubic-bezier(0.19, 1, 0.22, 1), border-color 170ms cubic-bezier(0.19, 1, 0.22, 1), box-shadow 170ms cubic-bezier(0.19, 1, 0.22, 1), transform 170ms cubic-bezier(0.19, 1, 0.22, 1);
}
.submit:hover:not(:disabled) {
  border-color: oklch(37% 0.14 255);
  background: oklch(40% 0.14 255);
  box-shadow: 0 9px 18px rgba(37, 85, 156, 0.2), inset 0 1px 0 oklch(100% 0 0 / 0.25);
  transform: translateY(-1px);
}
.submit:active:not(:disabled) {
  background: oklch(36% 0.135 255);
  transform: translateY(0) scale(0.985);
}
.submit:disabled {
  border-color: oklch(84% 0.014 250);
  background: oklch(89.5% 0.018 250);
  color: oklch(52% 0.02 250);
  box-shadow: none;
  opacity: 0.62;
  pointer-events: none;
}
.submit:hover:not(:disabled) svg {
  transform: translateX(2px);
}
.suggestions {
  position: absolute;
  z-index: 20;
  top: calc(100% + 10px);
  left: 0;
  right: 0;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: 0 20px 46px rgba(30, 39, 52, 0.13);
  transform-origin: top center;
  animation: suggestions-in 170ms cubic-bezier(0.19, 1, 0.22, 1);
}
.suggestion {
  display: flex;
  width: 100%;
  min-height: 58px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 11px 14px;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  color: var(--text);
  text-align: left;
  transition: background 150ms ease-out, color 150ms ease-out;
}
.suggestion svg {
  flex: 0 0 auto;
  width: 16px;
  height: 16px;
  stroke-width: 1.9;
}
.suggestion.muted {
  justify-content: flex-start;
}
.suggestion:last-child {
  border-bottom: 0;
}
.suggestion:hover {
  background: oklch(96.8% 0.012 255);
}
.suggestion strong,
.suggestion small {
  display: block;
}
.suggestion span {
  min-width: 0;
}
.suggestion strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.suggestion small {
  margin-top: 2px;
  color: var(--muted);
  font-size: 12px;
}
.suggestion b {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 13px;
}
.suggestion b svg {
  color: var(--muted-2);
  transition: color 160ms ease-out, transform 160ms ease-out;
}
.suggestion:hover b svg {
  color: var(--accent);
  transform: translateX(2px);
}
.spin {
  animation: icon-spin 900ms linear infinite;
}
.err {
  color: var(--rise);
}
@keyframes icon-spin {
  to { transform: rotate(360deg); }
}
@keyframes suggestions-in {
  from {
    opacity: 0;
    transform: translateY(-4px) scale(0.992);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
@media (max-width: 600px) {
  .search-box {
    grid-template-columns: 42px minmax(0, 1fr) auto;
  }
  .submit {
    grid-column: 1 / -1;
    width: 100%;
    margin: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .search-box,
  .search-symbol,
  .submit,
  .suggestion b svg {
    transition: none;
  }
  .suggestions,
  .spin {
    animation: none;
  }
}
</style>
