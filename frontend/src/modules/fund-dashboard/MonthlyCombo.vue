<script setup>
import { computed } from 'vue'
import { useChart } from '../../shared/charting/useChart'
import { fmtPct, money } from '../../shared/formatting/format'

const props = defineProps({ monthly: { type: Object, default: null } })
const RISE = 'oklch(49% 0.17 24)'
const FALL = 'oklch(46% 0.12 172)'
const ACCENT = 'oklch(45% 0.13 255)'
const LINE = 'oklch(89.6% 0.012 250)'
const LINE_STRONG = 'oklch(82.4% 0.018 250)'
const TEXT = 'oklch(24% 0.018 250)'
const MUTED = 'oklch(48% 0.022 250)'
const SURFACE_SOFT = 'oklch(97.4% 0.006 250)'
const RISE_SCALE = [
  'oklch(86% 0.075 24)',
  'oklch(78% 0.105 24)',
  'oklch(68% 0.145 24)',
  'oklch(58% 0.18 24)',
  'oklch(49% 0.17 24)',
]
const FALL_SCALE = [
  'oklch(84% 0.052 172)',
  'oklch(75% 0.07 172)',
  'oklch(65% 0.09 172)',
  'oklch(55% 0.11 172)',
  'oklch(46% 0.12 172)',
]
const RISE_BORDER_SCALE = [
  'oklch(74% 0.09 24)',
  'oklch(67% 0.118 24)',
  'oklch(59% 0.148 24)',
  'oklch(51% 0.162 24)',
  'oklch(43% 0.148 24)',
]
const FALL_BORDER_SCALE = [
  'oklch(72% 0.058 172)',
  'oklch(65% 0.074 172)',
  'oklch(57% 0.092 172)',
  'oklch(50% 0.105 172)',
  'oklch(42% 0.105 172)',
]

function yDomain(values, paddingRatio = 0.18) {
  const valid = values.filter((value) => Number.isFinite(value))
  if (!valid.length) return [-1, 1]
  const minValue = Math.min(...valid)
  const maxValue = Math.max(...valid)
  const magnitude = Math.max(1, Math.abs(minValue), Math.abs(maxValue))
  const padding = Math.max(0.8, magnitude * paddingRatio)
  if (minValue >= 0) return [0, maxValue + padding]
  if (maxValue <= 0) return [minValue - padding, 0]
  return [minValue - padding, maxValue + padding]
}

function barYDomain(values) {
  const valid = values.filter((value) => Number.isFinite(value))
  if (!valid.length) return [-1, 1]
  const minValue = Math.min(0, ...valid)
  const maxValue = Math.max(0, ...valid)
  const magnitude = Math.max(1, Math.abs(minValue), Math.abs(maxValue))
  const padding = Math.max(1.8, magnitude * 0.32)
  return [minValue - padding, maxValue + padding]
}

function roundedDomain(domain) {
  return [Math.floor(domain[0] / 5) * 5, Math.ceil(domain[1] / 5) * 5]
}

function barLevel(value, maxAbs) {
  const n = Number(value || 0)
  if (Math.abs(n) < 0.005) return -1
  return Math.max(0, Math.min(4, Math.ceil((Math.abs(n) / Math.max(1, maxAbs)) * 5) - 1))
}

function barColor(value, maxAbs) {
  const n = Number(value || 0)
  const level = barLevel(value, maxAbs)
  if (level < 0) return 'oklch(86% 0.008 250)'
  return n > 0 ? RISE_SCALE[level] : FALL_SCALE[level]
}

function barBorderColor(value, maxAbs) {
  const n = Number(value || 0)
  const level = barLevel(value, maxAbs)
  if (n > 0) return RISE_BORDER_SCALE[level]
  if (n < 0) return FALL_BORDER_SCALE[level]
  return LINE_STRONG
}

const currentMonths = computed(() =>
  (props.monthly?.items || [])
    .filter((item) => item.year === props.monthly?.currentYear)
    .sort((a, b) => a.month - b.month),
)

const latest = computed(() => currentMonths.value.at(-1))

function barDataItem(item, maxAbs) {
  return {
    value: item.pct,
    itemStyle: {
      color: barColor(item.pct, maxAbs),
      borderColor: barBorderColor(item.pct, maxAbs),
      borderWidth: 0.75,
      borderRadius: [3, 3, 3, 3],
    },
  }
}

const option = computed(() => {
  const cur = currentMonths.value
  const maxMonthAbs = Math.max(1, ...cur.map((item) => Math.abs(Number(item.pct || 0))))
  const monthDomain = roundedDomain(barYDomain(cur.map((item) => item.pct)))
  const cumulativeDomain = roundedDomain(yDomain(cur.map((item) => item.cumulativePct)))
  const labels = cur.map((item) => `${item.month}月`)
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      axisPointer: { show: false },
      formatter(param) {
        const point = cur[param?.dataIndex]
        if (!point) return ''
        return [
          `<strong>${point.year}年${point.month}月${point.partial ? '，尚未完整' : ''}</strong>`,
          `<div>月涨跌幅：${fmtPct(point.pct)}</div>`,
          `<div>年内累计：${fmtPct(point.cumulativePct)}</div>`,
          `<div>月初净值：${money(point.startNav)}</div>`,
          `<div>月末净值：${money(point.endNav)}</div>`,
          `<div>交易日：${point.tradeDays} 个</div>`,
        ].join('')
      },
      backgroundColor: 'rgba(253, 253, 252, 0.98)',
      borderColor: 'rgba(210, 216, 224, 0.92)',
      borderWidth: 1,
      padding: [10, 12],
      textStyle: { color: TEXT, fontSize: 12 },
      extraCssText: 'box-shadow: 0 14px 30px rgba(25,34,45,.16); border-radius: 11px;',
    },
    legend: {
      top: 8,
      left: 'center',
      itemWidth: 22,
      itemHeight: 10,
      textStyle: { color: TEXT, fontSize: 12 },
      data: ['月涨跌幅', '年内累计涨跌幅'],
    },
    grid: [
      { left: 64, right: 32, top: 58, height: 178, show: true, backgroundColor: SURFACE_SOFT },
      { left: 64, right: 32, top: 300, height: 178, show: true, backgroundColor: SURFACE_SOFT },
    ],
    xAxis: [
      {
        type: 'category',
        gridIndex: 0,
        data: labels,
        axisLabel: { show: false },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: LINE_STRONG } },
      },
      {
        type: 'category',
        gridIndex: 1,
        data: labels,
        axisLabel: { color: MUTED, margin: 22 },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: LINE_STRONG } },
      },
    ],
    yAxis: [
      {
        type: 'value',
        gridIndex: 0,
        min: monthDomain[0],
        max: monthDomain[1],
        axisLabel: { formatter: (value) => `${Math.round(value)}%`, color: MUTED },
        axisLine: { show: true, lineStyle: { color: LINE_STRONG } },
        splitLine: { lineStyle: { color: LINE } },
      },
      {
        type: 'value',
        gridIndex: 1,
        min: cumulativeDomain[0],
        max: cumulativeDomain[1],
        axisLabel: { formatter: (value) => `${Math.round(value)}%`, color: MUTED },
        axisLine: { show: true, lineStyle: { color: LINE_STRONG } },
        splitLine: { lineStyle: { color: LINE } },
      },
    ],
    graphic: [
      {
        type: 'text',
        left: 64,
        top: 34,
        style: { text: '月涨跌幅', fill: RISE, fontSize: 12, fontWeight: 700 },
        silent: true,
      },
      {
        type: 'text',
        left: 64,
        top: 276,
        style: { text: '年内累计涨跌幅', fill: ACCENT, fontSize: 12, fontWeight: 700 },
        silent: true,
      },
    ],
    series: [
      {
        name: '月涨跌幅',
        type: 'bar',
        xAxisIndex: 0,
        yAxisIndex: 0,
        barMaxWidth: 48,
        barMinHeight: 6,
        data: cur.map((item) => barDataItem(item, maxMonthAbs)),
        emphasis: { disabled: true },
        blur: { itemStyle: { opacity: 1 } },
        select: { disabled: true },
        label: {
          show: true,
          position: 'top',
          formatter: (p) => fmtPct(p.value),
          color: TEXT,
          fontSize: 11,
          fontWeight: 700,
        },
      },
      {
        name: '年内累计涨跌幅',
        type: 'line',
        yAxisIndex: 1,
        xAxisIndex: 1,
        smooth: false,
        symbol: 'circle',
        symbolSize: 8,
        data: cur.map((item) => item.cumulativePct),
        itemStyle: { color: 'oklch(99.1% 0.004 250)', borderColor: ACCENT, borderWidth: 2 },
        lineStyle: { color: ACCENT, width: 2.6 },
        emphasis: { disabled: true },
        blur: { itemStyle: { opacity: 1 }, lineStyle: { opacity: 1 } },
        select: { disabled: true },
      },
    ],
  }
})

const { elRef } = useChart(option)
</script>

<template>
  <article class="monthly-card combo-card">
    <div class="chart-head">
      <div class="chart-title">
        <h2>{{ monthly?.currentYear || '当年' }} 年表现拆解</h2>
        <p>上方面板显示单月涨跌幅，下方面板显示年内累计涨跌幅，和旧版 HTML 的阅读顺序保持一致。</p>
      </div>
      <div v-if="latest" class="latest-pill">
        <span>最新月份</span>
        <strong>{{ latest.month }}月 {{ fmtPct(latest.pct) }}</strong>
      </div>
    </div>
    <div ref="elRef" class="chart"></div>
  </article>
</template>

<style scoped>
.monthly-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}
.combo-card {
  padding: 24px 24px 20px;
}
.chart-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  margin-bottom: 16px;
}
.chart-title h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 850;
  line-height: 1.15;
}
.chart-title p {
  max-width: 78ch;
  margin: 7px 0 0;
  color: var(--muted);
  font-size: 13px;
}
.latest-pill {
  min-width: 132px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-soft);
  text-align: right;
}
.latest-pill span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  font-weight: 760;
}
.latest-pill strong {
  display: block;
  margin-top: 4px;
  font-size: 16px;
  font-weight: 850;
}
.chart {
  width: 100%;
  height: 520px;
}
@media (max-width: 980px) {
  .chart-head {
    flex-direction: column;
  }
  .latest-pill {
    text-align: left;
  }
  .chart {
    height: 470px;
  }
}
@media (max-width: 560px) {
  .combo-card {
    padding: 16px;
  }
  .chart {
    height: 420px;
  }
}
</style>
