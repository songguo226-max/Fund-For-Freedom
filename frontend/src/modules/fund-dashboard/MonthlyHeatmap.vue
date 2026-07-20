<script setup>
import { computed, ref } from 'vue'
import { fmtPct, money, pctState } from '../../shared/formatting/format'

const props = defineProps({ monthly: { type: Object, default: null } })

const monthLabels = Array.from({ length: 12 }, (_, index) => `${index + 1}月`)
const active = ref(null)

const items = computed(() => props.monthly?.items || [])
const maxAbs = computed(() => Math.max(1, ...items.value.map((item) => Math.abs(Number(item.pct || 0)))))

const rows = computed(() => {
  const years = [...(props.monthly?.previousYears || []), props.monthly?.currentYear]
    .filter(Boolean)
    .sort((a, b) => a - b)

  return years.map((year) => ({
    year,
    months: Array.from({ length: 12 }, (_, index) =>
      items.value.find((item) => item.year === year && item.month === index + 1) || null,
    ),
  }))
})

function level(item) {
  if (!item) return ''
  const value = Math.abs(Number(item.pct || 0))
  if (value < 0.005) return 'level-0'
  return `level-${Math.max(1, Math.min(5, Math.ceil((value / maxAbs.value) * 5)))}`
}

function cellClass(item) {
  if (!item) return ['empty']
  const isActive = active.value?.year === item.year && active.value?.month === item.month
  return ['has-value', pctState(item.pct), level(item), { partial: item.partial, 'is-active': isActive }]
}

function show(item, event) {
  if (!item) return
  const rect = event.currentTarget.getBoundingClientRect()
  active.value = {
    ...item,
    tooltip: {
      x: Math.min(window.innerWidth - 230, Math.max(10, rect.left + rect.width + 12)),
      y: Math.min(window.innerHeight - 170, Math.max(10, rect.top + rect.height / 2 - 62)),
    },
  }
}

function hide() {
  active.value = null
}
</script>

<template>
  <article class="monthly-card heatmap-card">
    <div class="chart-head">
      <div class="chart-title">
        <h2>基金月度涨跌幅热力图</h2>
        <p>横向比较同一月份的不同年份。红色代表上涨，绿色代表下跌，颜色越深表示幅度越大。</p>
      </div>
    </div>

    <div class="heatmap-shell">
      <div class="heatmap-grid" role="grid" aria-label="基金月度涨跌幅热力图">
        <div class="heat-corner" aria-hidden="true"></div>
        <div v-for="label in monthLabels" :key="label" class="heat-month">{{ label }}</div>

        <template v-for="row in rows" :key="row.year">
          <div class="heat-year">{{ row.year }}年</div>
          <component
            :is="item ? 'button' : 'div'"
            v-for="(item, index) in row.months"
            :key="`${row.year}-${index}`"
            class="heat-cell"
            :class="cellClass(item)"
            :type="item ? 'button' : undefined"
            @mouseenter="show(item, $event)"
            @mouseleave="hide"
            @focus="show(item, $event)"
            @blur="hide"
          >
            {{ item ? fmtPct(item.pct) : '暂无' }}
          </component>
        </template>
      </div>
    </div>

    <div class="heat-scale" aria-hidden="true">
      <div class="heat-gradient"></div>
      <div class="heat-scale-labels">
        <span>下跌更大</span>
        <span>接近持平</span>
        <span>上涨更大</span>
      </div>
      <div class="heat-scale-title">月涨跌幅色阶</div>
    </div>

    <p class="heat-note">虚线边框表示该月数据尚未完整，数值按最新已公布净值计算。</p>

    <div
      v-if="active"
      class="monthly-tooltip visible"
      :style="{ left: `${active.tooltip.x}px`, top: `${active.tooltip.y}px` }"
      role="tooltip"
    >
      <strong>{{ active.year }}年{{ active.month }}月{{ active.partial ? '，尚未完整' : '' }}</strong>
      <dl>
        <dt>月涨跌幅</dt><dd :class="pctState(active.pct)">{{ fmtPct(active.pct) }}</dd>
        <dt>年内累计</dt><dd :class="pctState(active.cumulativePct)">{{ fmtPct(active.cumulativePct) }}</dd>
        <dt>月初净值</dt><dd>{{ money(active.startNav) }}</dd>
        <dt>月末净值</dt><dd>{{ money(active.endNav) }}</dd>
        <dt>交易日</dt><dd>{{ active.tradeDays }} 个</dd>
      </dl>
    </div>
  </article>
</template>

<style scoped>
.monthly-card {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}
.heatmap-card {
  padding: 30px 34px 26px;
}
.chart-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  margin-bottom: 28px;
}
.chart-title h2 {
  margin: 0;
  font-size: 30px;
  font-weight: 850;
  line-height: 1.15;
}
.chart-title p {
  max-width: 78ch;
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 15px;
}
.heatmap-shell {
  overflow-x: auto;
  padding: 2px 0 4px;
}
.heatmap-grid {
  display: grid;
  grid-template-columns: 88px repeat(12, minmax(88px, 1fr));
  gap: 4px;
  min-width: 1180px;
  align-items: stretch;
}
.heat-corner,
.heat-month {
  min-height: 30px;
}
.heat-month {
  display: grid;
  place-items: center;
  color: var(--text);
  font-size: 15px;
  font-weight: 760;
}
.heat-year {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 12px;
  color: var(--text);
  font-size: 18px;
  font-weight: 850;
  white-space: nowrap;
}
.heat-cell {
  display: grid;
  place-items: center;
  min-height: 60px;
  border: 1px solid rgba(253, 253, 252, 0.82);
  border-radius: 4px;
  background: oklch(96.7% 0.006 250);
  color: var(--text);
  font: inherit;
  font-size: 15px;
  font-weight: 780;
  letter-spacing: 0;
  text-align: center;
}
button.heat-cell {
  cursor: default;
  transition: box-shadow 160ms ease, transform 160ms ease, border-color 160ms ease;
}
button.heat-cell:hover,
button.heat-cell:focus-visible,
button.heat-cell.is-active {
  z-index: 2;
  border-color: rgba(47, 57, 74, 0.34);
  box-shadow: 0 10px 22px rgba(30, 39, 52, 0.12);
  outline: none;
  transform: translateY(-1px);
}
.heat-cell.empty {
  color: var(--muted-2);
  background: oklch(95.2% 0.006 250);
}
.heat-cell.partial {
  outline: 2px dashed var(--muted);
  outline-offset: -6px;
}
.heat-cell.rise.level-1 { background: oklch(97.2% 0.012 24); color: oklch(32% 0.016 250); }
.heat-cell.rise.level-2 { background: oklch(94.8% 0.032 24); color: oklch(32% 0.016 250); }
.heat-cell.rise.level-3 { background: oklch(90.4% 0.063 24); color: oklch(25% 0.018 250); }
.heat-cell.rise.level-4 { background: oklch(82.5% 0.105 24); color: oklch(99% 0.004 250); }
.heat-cell.rise.level-5 { background: oklch(58.5% 0.19 24); color: oklch(99% 0.004 250); }
.heat-cell.fall.level-1 { background: oklch(96.4% 0.012 172); color: oklch(32% 0.016 250); }
.heat-cell.fall.level-2 { background: oklch(92.6% 0.033 172); color: oklch(32% 0.016 250); }
.heat-cell.fall.level-3 { background: oklch(84.8% 0.061 172); color: oklch(25% 0.018 250); }
.heat-cell.fall.level-4 { background: oklch(72.5% 0.095 172); color: oklch(99% 0.004 250); }
.heat-cell.fall.level-5 { background: oklch(54% 0.12 172); color: oklch(99% 0.004 250); }
.heat-cell.flat,
.heat-cell.level-0 {
  background: oklch(96% 0.004 250);
  color: var(--muted);
}
.heat-scale {
  width: min(760px, 72%);
  margin: 28px auto 0;
}
.heat-gradient {
  height: 22px;
  border-radius: 2px;
  background: linear-gradient(90deg, oklch(54% 0.12 172), oklch(84.8% 0.061 172), oklch(96.4% 0.006 250), oklch(90.4% 0.063 24), oklch(58.5% 0.19 24));
}
.heat-scale-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 7px;
  color: var(--text);
  font-size: 13px;
  font-weight: 720;
}
.heat-scale-title,
.heat-note {
  color: var(--muted);
  font-size: 13px;
}
.heat-scale-title {
  margin-top: 5px;
  font-weight: 760;
  text-align: center;
}
.heat-note {
  margin: 22px 0 0;
}
.monthly-tooltip {
  position: fixed;
  z-index: 80;
  width: 210px;
  padding: 10px 12px;
  border: 1px solid rgba(210, 216, 224, 0.92);
  border-radius: 11px;
  background: rgba(253, 253, 252, 0.98);
  box-shadow: 0 14px 30px rgba(25, 34, 45, 0.16);
  pointer-events: none;
}
.monthly-tooltip strong {
  display: block;
  margin-bottom: 7px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  font-weight: 850;
}
.monthly-tooltip dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 5px 14px;
  margin: 0;
  font-size: 12px;
}
.monthly-tooltip dt {
  color: var(--muted);
  white-space: nowrap;
}
.monthly-tooltip dd {
  margin: 0;
  font-weight: 820;
  text-align: right;
  white-space: nowrap;
}
@media (max-width: 980px) {
  .heatmap-card {
    padding: 22px 18px 20px;
  }
  .chart-head {
    flex-direction: column;
  }
  .chart-title h2 {
    font-size: 25px;
  }
  .heat-scale {
    width: min(820px, 92%);
  }
}
@media (max-width: 560px) {
  .heatmap-card {
    padding: 16px;
  }
  .chart-title h2 {
    font-size: 22px;
  }
  .heatmap-grid {
    min-width: 980px;
    grid-template-columns: 76px repeat(12, 74px);
  }
  .heat-cell {
    min-height: 54px;
    font-size: 13px;
  }
  .heat-year {
    font-size: 15px;
  }
  .heat-scale {
    width: 100%;
  }
}
</style>
