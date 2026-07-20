<script setup>
import { computed, ref } from 'vue'
import { fmtPct, money, pctState } from '../../shared/formatting/format'

const props = defineProps({
  months: { type: Array, default: () => [] },
})

const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const active = ref(null)

const tradingCells = computed(() =>
  props.months.flatMap((month) =>
    month.cells
      .filter((cell) => cell.type === 'trading')
      .map((cell) => ({ ...cell, year: month.year, month: month.month })),
  ).sort((a, b) => String(a.date).localeCompare(String(b.date))),
)

const stats = computed(() => {
  const cells = tradingCells.value
  if (!cells.length) return null
  const first = cells[0]
  const latest = cells[cells.length - 1]
  const maxGain = cells.reduce((best, item) => (item.pct > best.pct ? item : best), cells[0])
  const maxLoss = cells.reduce((best, item) => (item.pct < best.pct ? item : best), cells[0])
  const periodReturn = first.nav ? (latest.nav / first.nav - 1) * 100 : 0
  return { first, latest, maxGain, maxLoss, periodReturn, tradeDays: cells.length }
})

function cellClass(cell) {
  if (cell.type !== 'trading') return cell.type
  const n = Math.abs(Number(cell.pct || 0))
  const maxAbs = Math.max(...tradingCells.value.map((item) => Math.abs(Number(item.pct || 0))), 1)
  const level = n < 0.005 ? 0 : Math.max(1, Math.min(5, Math.round((n / maxAbs) * 5)))
  return ['trading', pctState(cell.pct), `level-${level}`]
}

function show(cell, event) {
  if (cell.type !== 'trading') return
  const rect = event.currentTarget.getBoundingClientRect()
  const width = 188
  const height = 96
  const gap = 10
  const margin = 10
  const anchorX = rect.left + rect.width / 2
  const placement = rect.top >= height + gap + margin ? 'top' : 'bottom'
  const maxLeft = Math.max(margin, window.innerWidth - width - margin)
  const left = Math.min(maxLeft, Math.max(margin, anchorX - width / 2))
  const top = placement === 'top' ? rect.top - height - gap : rect.bottom + gap
  const arrowX = Math.min(width - 14, Math.max(14, anchorX - left))
  active.value = {
    ...cell,
    x: left,
    y: Math.max(margin, top),
    arrowX,
    placement,
  }
}

function hide() {
  active.value = null
}
</script>

<template>
  <div class="calendar-experience">
    <section v-if="stats" class="calendar-overview" aria-label="收益日历数据概览">
      <div class="overview-card range">
        <span>统计区间</span>
        <strong>{{ stats.first.date }}<br>{{ stats.latest.date }}</strong>
        <small>共 {{ stats.tradeDays }} 个交易日</small>
      </div>
      <div class="overview-card">
        <span>区间累计涨跌幅</span>
        <strong :class="pctState(stats.periodReturn)">{{ fmtPct(stats.periodReturn) }}</strong>
        <small>{{ money(stats.first.nav) }} → {{ money(stats.latest.nav) }}</small>
      </div>
      <div class="overview-card">
        <span>区间最高单日涨幅</span>
        <strong class="rise">{{ fmtPct(stats.maxGain.pct) }}</strong>
        <small>{{ stats.maxGain.date }}</small>
      </div>
      <div class="overview-card">
        <span>区间最大单日跌幅</span>
        <strong class="fall">{{ fmtPct(stats.maxLoss.pct) }}</strong>
        <small>{{ stats.maxLoss.date }}</small>
      </div>
      <div class="overview-card">
        <span>最新单位净值</span>
        <strong>{{ money(stats.latest.nav) }}</strong>
        <small>累计净值 {{ money(stats.latest.cumulativeNav) }}</small>
      </div>
    </section>

    <div class="calendar-board">
      <section v-for="month in months" :key="`${month.year}-${month.month}`" class="month-card">
        <header class="month-head">
        <div>
          <h2>{{ month.year }}年{{ month.month }}月</h2>
          <p>{{ month.tradeDays }} 个交易日</p>
        </div>
        <div class="month-return" :class="pctState(month.monthReturn)">
          <span>月内涨跌</span>
          <strong>{{ fmtPct(month.monthReturn) }}</strong>
        </div>
      </header>
      <div class="month-metrics" aria-label="月度净值摘要">
        <div><span>月初净值</span><strong>{{ money(month.startNav) }}</strong></div>
        <div><span>月末净值</span><strong>{{ money(month.endNav) }}</strong></div>
        <div><span>交易日</span><strong>{{ month.tradeDays }}</strong></div>
      </div>
      <div class="weekdays"><span v-for="day in weekdays" :key="day">{{ day }}</span></div>
      <div class="calendar-grid">
        <component
          :is="cell.type === 'trading' ? 'button' : 'div'"
          v-for="(cell, index) in month.cells"
          :key="`${cell.date || 'b'}-${index}`"
          class="day-cell"
          :class="[cellClass(cell), { 'is-active': active?.date === cell.date }]"
          :type="cell.type === 'trading' ? 'button' : undefined"
          @mouseenter="show(cell, $event)"
          @mouseleave="hide"
          @focus="show(cell, $event)"
          @blur="hide"
        >
          <template v-if="cell.type === 'trading'">
            <span class="day-num">{{ cell.day }}</span>
            <span class="pct">{{ fmtPct(cell.pct) }}</span>
            <span class="nav">{{ money(cell.nav) }}</span>
          </template>
          <template v-else-if="cell.type === 'closed'">
            <span class="day-num">{{ cell.day }}</span>
            <span class="closed-label">休市</span>
          </template>
        </component>
      </div>
    </section>
  </div>

    <section class="legend" aria-label="颜色图例">
      <strong>图例</strong>
      <span class="legend-item"><i class="swatch rise level-5"></i>大幅上涨</span>
      <span class="legend-item"><i class="swatch rise level-1"></i>小幅上涨</span>
      <span class="legend-item"><i class="swatch flat-swatch"></i>平盘或休市</span>
      <span class="legend-item"><i class="swatch fall level-1"></i>小幅下跌</span>
      <span class="legend-item"><i class="swatch fall level-5"></i>大幅下跌</span>
      <span>红色代表上涨，绿色代表下跌，颜色越深代表单日涨跌幅越大。</span>
    </section>

    <div
      v-if="active"
      class="calendar-tooltip"
      :class="pctState(active.pct)"
      :data-placement="active.placement"
      :style="{ left: `${active.x}px`, top: `${active.y}px`, '--arrow-x': `${active.arrowX}px` }"
      role="tooltip"
    >
      <div class="tip-date"><span>{{ active.date }}</span><small>交易日</small></div>
      <dl>
        <dt>单位净值</dt><dd>{{ money(active.nav) }}</dd>
        <dt>累计净值</dt><dd>{{ money(active.cumulativeNav) }}</dd>
        <dt>当日涨跌幅</dt><dd :class="pctState(active.pct)">{{ fmtPct(active.pct) }}</dd>
      </dl>
    </div>
  </div>
</template>

<style scoped>
.calendar-experience {
  display: grid;
  gap: 22px;
}
.calendar-overview {
  display: grid;
  grid-template-columns: 1.25fr repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.overview-card {
  min-height: 112px;
  padding: 17px 18px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--surface);
  box-shadow: 0 8px 22px rgba(25, 34, 45, 0.045);
}
.overview-card span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 760;
}
.overview-card strong {
  display: block;
  margin-top: 11px;
  font-size: 25px;
  font-weight: 850;
  line-height: 1.1;
}
.overview-card.range strong {
  font-size: 19px;
  line-height: 1.35;
}
.overview-card small {
  display: block;
  margin-top: 9px;
  color: var(--muted-2);
  font-size: 12px;
}
.calendar-board {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 720px), 1fr));
  justify-items: center;
  align-items: start;
  gap: 20px;
}
.month-card {
  width: 100%;
  max-width: 800px;
  padding: 20px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: var(--surface);
  box-shadow: 0 12px 32px rgba(25, 34, 45, 0.065);
}
.month-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line);
}
.month-head h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 850;
  line-height: 1.2;
}
.month-head p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}
.month-return {
  min-width: 116px;
  text-align: right;
}
.month-return span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  font-weight: 760;
}
.month-return strong {
  display: block;
  margin-top: 3px;
  font-size: 23px;
  font-weight: 880;
  line-height: 1.05;
}
.month-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 14px 0 16px;
}
.month-metrics div {
  padding: 10px;
  border: 1px solid oklch(92.5% 0.008 250);
  border-radius: 10px;
  background: oklch(98.3% 0.004 250);
}
.month-metrics span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 760;
}
.month-metrics strong {
  display: block;
  margin-top: 4px;
  font-size: 16px;
  font-weight: 820;
}
.weekdays,
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 7px;
}
.weekdays {
  margin-bottom: 7px;
}
.weekdays span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
  text-align: center;
}
.weekdays span:first-child,
.weekdays span:last-child {
  color: oklch(67% 0.015 250);
}
.day-cell {
  position: relative;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 11px;
  min-width: 0;
  font: inherit;
  text-align: left;
}
.blank {
  visibility: hidden;
  pointer-events: none;
}
.closed {
  min-height: 82px;
  aspect-ratio: 1.08 / 1;
  padding: 8px;
  border-color: oklch(94% 0.007 250);
  background: oklch(95.5% 0.006 250);
  color: var(--muted-2);
}
.day-num {
  align-self: start;
  color: rgba(32, 35, 40, 0.7);
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
}
.trading {
  display: grid;
  grid-template-rows: 13px minmax(20px, 1fr) 16px;
  align-items: center;
  width: 100%;
  min-height: 82px;
  aspect-ratio: 1.08 / 1;
  padding: 7px 8px;
  cursor: default;
  border-color: rgba(255, 255, 255, 0.68);
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}
.trading:hover,
.trading:focus-visible,
.trading.is-active {
  z-index: 2;
  transform: translateY(-1px);
  border-color: rgba(98, 113, 130, 0.2);
  box-shadow: 0 8px 18px rgba(25, 34, 45, 0.08), 0 0 0 2px rgba(109, 123, 139, 0.08);
  outline: none;
}
.trading.rise:hover,
.trading.rise:focus-visible,
.trading.rise.is-active {
  border-color: rgba(189, 47, 60, 0.24);
  box-shadow: 0 10px 20px rgba(189, 47, 60, 0.13), 0 0 0 2px rgba(189, 47, 60, 0.08);
}
.trading.fall:hover,
.trading.fall:focus-visible,
.trading.fall.is-active {
  border-color: rgba(8, 123, 99, 0.24);
  box-shadow: 0 10px 20px rgba(8, 123, 99, 0.13), 0 0 0 2px rgba(8, 123, 99, 0.08);
}
.pct {
  align-self: center;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  font-size: 18px;
  font-weight: 840;
  line-height: 1;
  text-align: center;
  white-space: nowrap;
}
.nav {
  align-self: end;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  color: rgba(32, 35, 40, 0.72);
  font-size: 11px;
  font-weight: 720;
  line-height: 1.1;
  text-align: center;
  white-space: nowrap;
}
.closed-label {
  position: absolute;
  left: 8px;
  bottom: 8px;
  color: var(--muted-2);
  font-size: 11px;
  font-weight: 700;
}
.trading.rise .pct,
.trading.rise .nav { color: var(--rise); }
.trading.fall .pct,
.trading.fall .nav { color: var(--fall); }
.rise.level-1 { background: oklch(97.2% 0.012 24); }
.rise.level-2 { background: oklch(94.8% 0.032 24); }
.rise.level-3 { background: oklch(90.4% 0.063 24); }
.rise.level-4 { background: oklch(82.5% 0.105 24); }
.rise.level-5 { background: oklch(76.5% 0.13 24); }
.fall.level-1 { background: oklch(96.4% 0.012 172); }
.fall.level-2 { background: oklch(92.6% 0.033 172); }
.fall.level-3 { background: oklch(84.8% 0.061 172); }
.fall.level-4 { background: oklch(72.5% 0.095 172); }
.fall.level-5 { background: oklch(69% 0.105 172); }
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
  align-items: center;
  padding: 16px 18px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--surface);
  box-shadow: 0 8px 22px rgba(25, 34, 45, 0.045);
  color: var(--muted);
  font-size: 13px;
}
.legend strong {
  color: var(--text);
}
.legend-item {
  display: inline-flex;
  gap: 7px;
  align-items: center;
  white-space: nowrap;
}
.swatch {
  width: 18px;
  height: 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
}
.swatch.flat-swatch {
  background: oklch(95.5% 0.006 250);
}
.calendar-tooltip {
  position: fixed;
  z-index: 50;
  box-sizing: border-box;
  width: 188px;
  padding: 9px 10px;
  border: 1px solid rgba(210, 216, 224, 0.86);
  border-radius: 11px;
  background: oklch(99.2% 0.004 250);
  box-shadow: 0 10px 24px rgba(31, 41, 55, 0.12);
  pointer-events: none;
}
.calendar-tooltip::before,
.calendar-tooltip::after {
  position: absolute;
  left: var(--arrow-x, 94px);
  width: 0;
  height: 0;
  content: "";
  transform: translateX(-50%);
}
.calendar-tooltip[data-placement="top"]::before {
  bottom: -8px;
  border-top: 8px solid rgba(210, 216, 224, 0.86);
  border-right: 8px solid transparent;
  border-left: 8px solid transparent;
}
.calendar-tooltip[data-placement="top"]::after {
  bottom: -7px;
  border-top: 7px solid oklch(99.2% 0.004 250);
  border-right: 7px solid transparent;
  border-left: 7px solid transparent;
}
.calendar-tooltip[data-placement="bottom"]::before {
  top: -8px;
  border-right: 8px solid transparent;
  border-bottom: 8px solid rgba(210, 216, 224, 0.86);
  border-left: 8px solid transparent;
}
.calendar-tooltip[data-placement="bottom"]::after {
  top: -7px;
  border-right: 7px solid transparent;
  border-bottom: 7px solid oklch(99.2% 0.004 250);
  border-left: 7px solid transparent;
}
.calendar-tooltip.rise {
  border-color: rgba(189, 47, 60, 0.2);
  box-shadow: 0 10px 24px rgba(189, 47, 60, 0.1);
}
.calendar-tooltip.fall {
  border-color: rgba(8, 123, 99, 0.2);
  box-shadow: 0 10px 24px rgba(8, 123, 99, 0.1);
}
.calendar-tooltip.rise[data-placement="top"]::before {
  border-top-color: rgba(189, 47, 60, 0.2);
}
.calendar-tooltip.rise[data-placement="bottom"]::before {
  border-bottom-color: rgba(189, 47, 60, 0.2);
}
.calendar-tooltip.fall[data-placement="top"]::before {
  border-top-color: rgba(8, 123, 99, 0.2);
}
.calendar-tooltip.fall[data-placement="bottom"]::before {
  border-bottom-color: rgba(8, 123, 99, 0.2);
}
.tip-date {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(230, 234, 239, 0.88);
  color: var(--text);
  font-size: 13px;
  font-weight: 850;
}
.tip-date small {
  color: var(--muted-2);
  font-size: 10px;
  font-weight: 720;
}
.calendar-tooltip dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 14px;
  margin: 0;
  font-size: 11px;
}
.calendar-tooltip dt {
  color: var(--muted);
  font-weight: 620;
  white-space: nowrap;
}
.calendar-tooltip dd {
  margin: 0;
  color: var(--text);
  font-weight: 850;
  text-align: right;
  white-space: nowrap;
}
@media (max-width: 560px) {
  .calendar-overview {
    grid-template-columns: 1fr;
  }
  .month-card {
    padding: 11px;
    border-radius: 16px;
  }
  .month-head {
    align-items: flex-start;
  }
  .month-head h2 {
    font-size: 19px;
  }
  .month-metrics {
    gap: 5px;
  }
  .month-metrics div {
    padding: 7px 5px;
  }
  .weekdays,
  .calendar-grid {
    gap: 4px;
  }
  .trading,
  .closed {
    min-height: 48px;
    aspect-ratio: 0.96 / 1;
    padding: 5px 4px;
  }
  .trading {
    grid-template-rows: 10px minmax(16px, 1fr);
  }
  .pct {
    font-size: 8.8px;
    font-weight: 820;
  }
  .nav { display: none; }
  .closed-label {
    left: 5px;
    bottom: 6px;
    font-size: 9px;
  }
}
@media (min-width: 1540px) {
  .calendar-board {
    grid-template-columns: repeat(2, minmax(720px, 1fr));
  }
}
@media (max-width: 1120px) {
  .calendar-overview {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .overview-card.range {
    grid-column: span 2;
  }
}
@media (max-width: 920px) {
  .calendar-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 720px) {
  .calendar-overview {
    grid-template-columns: 1fr;
  }
  .overview-card.range {
    grid-column: auto;
  }
}
</style>
