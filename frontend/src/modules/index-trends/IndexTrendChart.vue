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

function formatClose(value, options = {}) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '--'
  return number.toLocaleString('en-US', {
    minimumFractionDigits: options.minimumFractionDigits ?? 0,
    maximumFractionDigits: options.maximumFractionDigits ?? 2,
  })
}

function formatPct(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '--'
  return `${number > 0 ? '+' : ''}${number.toFixed(2)}%`
}

function formatMonth(value) {
  if (!value) return ''
  return String(value).slice(0, 7)
}

function pctClass(value) {
  const number = Number(value)
  if (number > 0) return 'tooltip-rise'
  if (number < 0) return 'tooltip-fall'
  return 'tooltip-flat'
}

const option = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'line',
      lineStyle: { color: '#9eb1d9', type: 'dashed' },
    },
    formatter(params) {
      const point = params?.[0]?.data
      if (!point) return ''
      return [
        `<div class="index-tooltip-date">${point.date}</div>`,
        '<div class="index-tooltip-row">',
        '<span class="index-tooltip-dot"></span>',
        `<span>${props.item.name}</span>`,
        `<strong>${formatClose(point.close, { minimumFractionDigits: 2 })}</strong>`,
        '</div>',
        '<div class="index-tooltip-row">',
        '<span class="index-tooltip-spacer"></span>',
        '<span>涨跌幅</span>',
        `<strong class="${pctClass(point.pct)}">${formatPct(point.pct)}</strong>`,
        '</div>',
      ].join('')
    },
  },
  grid: { top: 20, right: 18, bottom: 30, left: 58 },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: points.value.map((point) => point.date),
    axisLine: { lineStyle: { color: '#d4dce7' } },
    axisTick: { show: false },
    axisLabel: {
      color: '#667085',
      hideOverlap: true,
      formatter: formatMonth,
    },
  },
  yAxis: {
    type: 'value',
    scale: true,
    axisLabel: {
      color: '#667085',
      formatter: (value) => formatClose(value),
    },
    splitLine: { lineStyle: { color: '#e8edf4' } },
  },
  series: [
    {
      name: props.item.name,
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: points.value.map((point) => ({
        value: point.close,
        date: point.date,
        close: point.close,
        pct: point.pct,
      })),
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
      <span>最新 {{ latest.date }} · {{ formatClose(latest.close, { minimumFractionDigits: 2 }) }}</span>
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

:global(.index-tooltip-date) {
  margin-bottom: 8px;
  color: oklch(42% 0.03 250);
  font-size: 12px;
}

:global(.index-tooltip-row) {
  display: grid;
  grid-template-columns: 10px minmax(92px, 1fr) auto;
  align-items: center;
  gap: 7px;
  color: oklch(34% 0.025 250);
  font-size: 12px;
  line-height: 1.5;
}

:global(.index-tooltip-row + .index-tooltip-row) {
  margin-top: 4px;
}

:global(.index-tooltip-dot) {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: #3452b4;
}

:global(.index-tooltip-spacer) {
  width: 9px;
}

:global(.index-tooltip-row strong) {
  justify-self: end;
  color: oklch(35% 0.02 250);
  font-weight: 760;
}

:global(.index-tooltip-row .tooltip-rise) {
  color: var(--rise);
}

:global(.index-tooltip-row .tooltip-fall) {
  color: var(--fall);
}

:global(.index-tooltip-row .tooltip-flat) {
  color: var(--muted);
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
