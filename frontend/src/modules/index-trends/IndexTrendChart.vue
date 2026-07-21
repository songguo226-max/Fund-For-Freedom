<script setup>
import { computed } from 'vue'
import { useChart } from '../../shared/charting/useChart'

const props = defineProps({
  item: { type: Object, required: true },
})

const points = computed(() => props.item.ranges?.[0]?.points || [])
const latest = computed(() => points.value.at(-1))
const first = computed(() => points.value[0])
const changeClass = computed(() => {
  const value = latest.value?.cumulativePct || 0
  if (value > 0) return 'rise'
  if (value < 0) return 'fall'
  return 'flat'
})

const option = computed(() => ({
  tooltip: {
    trigger: 'axis',
    valueFormatter: (value) => Number(value).toFixed(4),
  },
  grid: { top: 20, right: 18, bottom: 30, left: 46 },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: points.value.map((point) => point.date),
    axisLine: { lineStyle: { color: '#d4dce7' } },
    axisTick: { show: false },
    axisLabel: { color: '#667085', hideOverlap: true },
  },
  yAxis: {
    type: 'value',
    scale: true,
    axisLabel: { color: '#667085' },
    splitLine: { lineStyle: { color: '#e8edf4' } },
  },
  series: [
    {
      name: props.item.name,
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: points.value.map((point) => point.nav),
      lineStyle: { width: 2, color: '#3452b4' },
      itemStyle: { color: '#3452b4' },
      areaStyle: { color: 'rgba(52, 82, 180, 0.08)' },
    },
  ],
}))

const { elRef } = useChart(option)
</script>

<template>
  <article class="index-chart panel">
    <header class="chart-head">
      <div>
        <p>{{ item.market }} · {{ item.source }}</p>
        <h2>{{ item.name }}</h2>
      </div>
      <strong :class="changeClass">{{ latest ? `${latest.cumulativePct.toFixed(2)}%` : '--' }}</strong>
    </header>

    <div v-if="item.error" class="chart-empty">{{ item.error }}</div>
    <div v-else-if="points.length < 2" class="chart-empty">暂无足够数据</div>
    <div v-else ref="elRef" class="chart"></div>

    <footer v-if="first && latest" class="chart-meta">
      <span>{{ first.date }}</span>
      <span>最新 {{ latest.date }} · {{ latest.nav.toFixed(4) }}</span>
    </footer>
  </article>
</template>

<style scoped>
.index-chart {
  display: grid;
  min-width: 0;
  padding: 16px;
  gap: 12px;
}

.chart-head {
  display: flex;
  min-height: 48px;
  align-items: start;
  justify-content: space-between;
  gap: 14px;
}

.chart-head p,
.chart-head h2 {
  margin: 0;
}

.chart-head p {
  color: var(--muted);
  font-size: 12px;
  font-weight: 720;
}

.chart-head h2 {
  margin-top: 3px;
  font-size: 17px;
  line-height: 1.25;
}

.chart-head strong {
  flex: 0 0 auto;
  font-size: 18px;
  line-height: 1.2;
}

.chart {
  width: 100%;
  height: 250px;
}

.chart-empty {
  display: grid;
  min-height: 250px;
  place-items: center;
  border-radius: var(--radius-md);
  background: var(--surface-soft);
  color: var(--muted);
  text-align: center;
  padding: 18px;
}

.chart-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--muted);
  font-size: 12px;
}

@media (max-width: 560px) {
  .chart {
    height: 220px;
  }

  .chart-meta {
    flex-direction: column;
    gap: 2px;
  }
}
</style>
