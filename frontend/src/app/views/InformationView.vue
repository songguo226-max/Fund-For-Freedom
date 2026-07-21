<script setup>
import { LineChart, RefreshCw } from 'lucide-vue-next'
import { onMounted, reactive, ref, watch } from 'vue'
import { api } from '../../integrations/fund-api'
import IndexTrendChart from '../../modules/index-trends/IndexTrendChart.vue'
import AsyncBlock from '../../shared/ui/AsyncBlock.vue'

const ranges = [
  { value: '1m', label: '1个月' },
  { value: '3m', label: '3个月' },
  { value: '6m', label: '半年' },
  { value: '1y', label: '1年' },
  { value: '3y', label: '3年' },
  { value: '5y', label: '5年' },
  { value: 'all', label: '成立来' },
]

const selectedRange = ref('1y')
const state = reactive({ loading: false, error: '', data: null })

async function load() {
  state.loading = true
  state.error = ''
  try {
    state.data = await api.indexTrends({ ranges: selectedRange.value })
  } catch (error) {
    state.error = error.message || '指数走势加载失败'
  } finally {
    state.loading = false
  }
}

onMounted(load)
watch(selectedRange, load)
</script>

<template>
  <main class="shell page info-page">
    <section class="section-head">
      <p class="eyebrow"><LineChart />信息</p>
      <div class="head-row">
        <div>
          <h1>指数净值走势</h1>
          <p>标普500、纳斯达克100、恒生、上证、沪深300、中证500。</p>
        </div>
        <button class="text-button" type="button" @click="load"><RefreshCw />刷新</button>
      </div>
    </section>

    <section class="range-bar" aria-label="走势区间">
      <button
        v-for="range in ranges"
        :key="range.value"
        type="button"
        :class="{ on: selectedRange === range.value }"
        @click="selectedRange = range.value"
      >
        {{ range.label }}
      </button>
    </section>

    <AsyncBlock :state="state" @retry="load">
      <template #default="{ data }">
        <section class="index-grid" aria-label="指数净值走势图">
          <IndexTrendChart v-for="item in data" :key="item.id" :item="item" />
        </section>
      </template>
    </AsyncBlock>
  </main>
</template>

<style scoped>
.info-page {
  display: grid;
  align-content: start;
  gap: 16px;
  padding-top: 142px;
}

.section-head {
  display: grid;
  gap: 8px;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
  margin: 0;
  color: var(--accent);
  font-size: 13px;
  font-weight: 820;
}

.eyebrow svg {
  width: 15px;
  height: 15px;
  stroke-width: 2;
}

h1,
p {
  margin: 0;
}

h1 {
  font-size: 34px;
  line-height: 1.12;
}

.head-row {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
}

.section-head p {
  margin-top: 10px;
  max-width: 64ch;
  color: var(--muted);
}

.range-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.range-bar button {
  min-width: 68px;
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--text);
  transition:
    background 160ms ease-out,
    border-color 160ms ease-out,
    color 160ms ease-out;
}

.range-bar button:hover {
  border-color: var(--line-strong);
  background: var(--surface-soft);
}

.range-bar button.on {
  border-color: var(--accent);
  background: var(--accent);
  color: oklch(98% 0.004 250);
}

.index-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

@media (max-width: 920px) {
  .index-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .head-row {
    align-items: start;
    flex-direction: column;
  }

  h1 {
    font-size: 30px;
  }

  .range-bar button {
    min-width: 62px;
  }
}
</style>
