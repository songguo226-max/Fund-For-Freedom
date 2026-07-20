<script setup>
import { ArrowLeft, BarChart3, CalendarDays, DownloadCloud, LineChart, RefreshCw, Star } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../integrations/fund-api'
import { fmtPct, money, pctState } from '../../shared/formatting/format'
import AsyncBlock from '../../shared/ui/AsyncBlock.vue'
import { useWatchlist } from '../watchlist/useWatchlist'
import MonthlyCombo from './MonthlyCombo.vue'
import MonthlyHeatmap from './MonthlyHeatmap.vue'
import NavTrend from './NavTrend.vue'
import ReturnCalendar from './ReturnCalendar.vue'
import { useFund } from './useFund'

const props = defineProps({ code: { type: String, required: true } })
const router = useRouter()
const fund = useFund(() => props.code)
const { toggleFavorite, isFavorite } = useWatchlist()
const tab = ref('calendar')
const source = ref('')
const range = ref('1y')

const meta = computed(() => fund.meta.data)

onMounted(() => fund.load(range.value))
watch(() => props.code, () => fund.load(range.value))

function changeSource() {
  fund.setSource(source.value)
}

function changeRange() {
  fund.load(range.value)
}

function download(type) {
  window.open(api.exportUrl(props.code, type, source.value), '_blank')
}
</script>

<template>
  <main class="shell page detail">
    <header class="toolbar">
      <button class="icon-button" title="返回" @click="router.push('/')"><ArrowLeft /></button>
      <div class="title">
        <h1>{{ meta?.name || `基金 ${code}` }}</h1>
        <p>{{ code }}</p>
      </div>
      <div class="tools">
        <select v-model="source" class="field" name="data-source" @change="changeSource">
          <option value="">自动数据源</option>
          <option value="eastmoney">东方财富</option>
          <option value="morningstar">晨星</option>
        </select>
        <button class="text-button" @click="fund.load(range)">
          <RefreshCw />刷新
        </button>
        <button class="text-button" @click="toggleFavorite({ code, name: meta?.name || code, type: meta?.type })">
          <Star :fill="isFavorite(code) ? 'currentColor' : 'none'" />{{ isFavorite(code) ? '已自选' : '自选' }}
        </button>
      </div>
    </header>

    <section class="fund-hero">
      <div class="hero-copy">
        <p class="eyebrow"><CalendarDays />基金收益日历</p>
        <h2>{{ meta?.name || `基金 ${code}` }}</h2>
        <p class="hero-desc">
          {{ code }}，按最近已公布净值生成收益日历。红色代表上涨，绿色代表下跌，鼠标悬停可查看每日净值明细。
        </p>
      </div>
      <aside class="latest-card" aria-label="最新交易日摘要">
        <div>
          <div class="label">最新交易日</div>
          <div class="latest-date">{{ meta?.latestDate || '暂无' }}</div>
        </div>
        <div class="latest-main">
          <div>
            <div class="label">最新涨跌幅</div>
            <strong :class="pctState(meta?.latestPct)">{{ fmtPct(meta?.latestPct) }}</strong>
          </div>
          <div class="latest-nav">
            <div class="label">最新单位净值</div>
            <b>{{ money(meta?.latestNav) }}</b>
          </div>
        </div>
      </aside>
    </section>

    <nav class="tabs">
      <button :class="{ on: tab === 'calendar' }" @click="tab = 'calendar'"><CalendarDays />收益日历</button>
      <button :class="{ on: tab === 'monthly' }" @click="tab = 'monthly'"><BarChart3 />月度分析</button>
      <button :class="{ on: tab === 'trend' }" @click="tab = 'trend'"><LineChart />走势</button>
      <span class="spacer"></span>
      <button class="text-button" @click="download('daily')"><DownloadCloud />日数据</button>
      <button class="text-button" @click="download('monthly')"><DownloadCloud />月数据</button>
    </nav>

    <section v-if="tab === 'calendar'">
      <AsyncBlock :state="fund.calendar" @retry="fund.load(range)">
        <template #default="{ data }"><ReturnCalendar :months="data" /></template>
      </AsyncBlock>
    </section>

    <section v-if="tab === 'monthly'" class="chart-stack">
      <AsyncBlock :state="fund.monthly" @retry="fund.load(range)">
        <template #default="{ data }">
          <MonthlyHeatmap :monthly="data" />
          <MonthlyCombo :monthly="data" />
        </template>
      </AsyncBlock>
    </section>

    <section v-if="tab === 'trend'">
      <div class="range-row">
        <select v-model="range" class="field" name="trend-range" @change="changeRange">
          <option value="3m">近 3 月</option>
          <option value="6m">近 6 月</option>
          <option value="1y">近 1 年</option>
          <option value="3y">近 3 年</option>
          <option value="all">全部</option>
        </select>
      </div>
      <AsyncBlock :state="fund.trend" @retry="fund.load(range)">
        <template #default="{ data }">
          <div class="panel chart-panel">
            <h2>净值走势</h2>
            <NavTrend :points="data" />
          </div>
        </template>
      </AsyncBlock>
    </section>
  </main>
</template>

<style scoped>
.detail {
  display: grid;
  gap: 16px;
}
.toolbar {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
}
.title h1 {
  margin: 0;
  overflow-wrap: anywhere;
  font-size: 24px;
  line-height: 1.2;
}
.title p {
  margin: 3px 0 0;
  color: var(--muted);
  font-size: 13px;
}
.tools {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}
.tools .field {
  padding: 0 10px;
}
.fund-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 384px);
  gap: 18px;
  align-items: stretch;
}
.hero-copy,
.latest-card {
  border: 1px solid var(--line);
  border-radius: 20px;
  background: var(--surface);
  box-shadow: var(--shadow);
}
.hero-copy {
  min-height: 176px;
  padding: 26px 28px;
}
.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
  margin: 0 0 13px;
  padding: 5px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface-soft);
  color: var(--muted);
  font-size: 12px;
  font-weight: 760;
}
.eyebrow svg {
  width: 14px;
  height: 14px;
  stroke-width: 1.9;
}
.hero-copy h2 {
  margin: 0;
  overflow-wrap: anywhere;
  font-size: 38px;
  font-weight: 850;
  line-height: 1.12;
}
.hero-desc {
  max-width: 74ch;
  margin: 14px 0 0;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.75;
}
.latest-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 24px;
}
.label {
  color: var(--muted);
  font-size: 12px;
  font-weight: 760;
}
.latest-date {
  margin-top: 4px;
  font-size: 20px;
  font-weight: 820;
}
.latest-main {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
  margin-top: 22px;
}
.latest-main strong {
  display: block;
  margin-top: 6px;
  font-size: 36px;
  font-weight: 880;
  line-height: 1;
}
.latest-nav {
  text-align: right;
}
.latest-nav b {
  display: block;
  margin-top: 4px;
  font-size: 23px;
  font-weight: 820;
}
.tabs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.tabs > button:not(.text-button) {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 36px;
  padding: 0 13px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--text);
}
.tabs > button:not(.text-button) svg {
  width: 16px;
  height: 16px;
  color: var(--muted);
  stroke-width: 1.9;
}
.tabs > button.on {
  border-color: var(--text);
  background: var(--text);
  color: oklch(98% 0.004 250);
}
.tabs > button.on svg {
  color: currentColor;
}
.spacer {
  flex: 1;
}
.chart-stack {
  display: grid;
  gap: 20px;
}
.chart-panel {
  padding: 16px;
}
.chart-panel h2 {
  margin: 0 0 12px;
  font-size: 16px;
}
.range-row {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}
.range-row .field {
  padding: 0 10px;
}
@media (max-width: 860px) {
  .toolbar {
    grid-template-columns: auto 1fr;
  }
  .tools {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }
  .fund-hero {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 560px) {
  .hero-copy,
  .latest-card {
    border-radius: 17px;
    padding: 17px;
  }
  .hero-copy h2 {
    font-size: 30px;
  }
  .hero-desc {
    margin-top: 10px;
    font-size: 13px;
    line-height: 1.65;
  }
  .latest-main {
    align-items: flex-start;
    flex-direction: column;
  }
  .latest-nav {
    text-align: left;
  }
  .spacer {
    display: none;
  }
}
</style>
