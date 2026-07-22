<script setup>
import { ExternalLink, Newspaper, RefreshCw } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../../integrations/fund-api'
import { useWatchlist } from '../watchlist/useWatchlist'

const { favorites, recents } = useWatchlist()
const state = reactive({ loading: false, error: '', data: null })
const activeReport = ref('weekly')
const activeSource = ref('all')

const sourceSummary = computed(() => state.data?.sources || [])
const rankedHotlistSources = new Set(['cls', 'eastmoney', 'gelonghui', 'xueqiu'])
const weeklySnapshotSources = new Set(['cls', 'eastmoney', 'gelonghui', 'xueqiu'])
const hiddenSummarySources = new Set(['eastmoney', 'gelonghui', 'xueqiu'])

const visibleItems = computed(() => {
  const items = state.data?.items || []
  const sourceItems = activeSource.value === 'all'
    ? items
    : items.filter((item) => item.sourceId === activeSource.value)

  if (activeReport.value === 'weekly') {
    return sourceItems.filter((item) => {
      if (weeklySnapshotSources.has(item.sourceId)) return item.reportBucket === 'weekly' && item.rankSnapshotDate
      return item.reportBucket === 'weekly'
    })
  }

  return limitDailyBySource(sortDailyItems(sourceItems.filter((item) => !item.rankSnapshotDate)), 7)
})

const activeListLabel = computed(() => {
  const reportName = activeReport.value === 'weekly' ? '周报' : '日报'
  if (activeSource.value === 'all') return reportName
  const sourceName = sourceSummary.value.find((source) => source.sourceId === activeSource.value)?.sourceName || '当前来源'
  return `${sourceName}${reportName}`
})

const isAggregateList = computed(() => activeSource.value === 'all' && ['weekly', 'daily'].includes(activeReport.value))

async function syncWatchlist() {
  await api.syncNewsWatchlist({
    favorites: favorites.value,
    recents: recents.value,
  })
}

async function load(force = false) {
  state.loading = true
  state.error = ''
  try {
    await syncWatchlist()
    state.data = await api.newsRefresh({ force, staleOk: !force, limit: 30 })
    if (activeSource.value !== 'all' && !sourceSummary.value.some((source) => source.sourceId === activeSource.value)) {
      activeSource.value = 'all'
    }
  } catch (error) {
    state.error = error.message || '新闻资讯加载失败'
  } finally {
    state.loading = false
  }
}

function setReport(type) {
  activeReport.value = type
}

function limitDailyBySource(items, limit) {
  const counts = new Map()
  return items.filter((item) => {
    const count = counts.get(item.sourceId) || 0
    if (count >= limit) return false
    counts.set(item.sourceId, count + 1)
    return true
  })
}

function sortDailyItems(items) {
  return [...items].sort((a, b) => {
    if (rankedHotlistSources.has(a.sourceId) && a.sourceId === b.sourceId) {
      return topicRank(a) - topicRank(b)
    }
    return 0
  })
}

function topicRank(item) {
  const match = item.summary?.match(/第(\d+)名/)
  return match ? Number(match[1]) : Number.MAX_SAFE_INTEGER
}

function itemDateValue(item) {
  return activeReport.value === 'weekly'
    ? item.rankSnapshotDate || item.publishedAt
    : item.publishedAt
}

function formatDateLabel(item) {
  const value = itemDateValue(item)
  if (!value) return '今日'
  if (activeReport.value === 'weekly') {
    const match = String(value).match(/^\d{4}[-/](\d{2})[-/](\d{2})/)
    return match ? `${match[1]}/${match[2]}` : value
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function isFeedStyle(item) {
  return rankedHotlistSources.has(item.sourceId)
}

function showSourceTag(item) {
  if (activeSource.value === 'all') return Boolean(item.sourceName)
  return !rankedHotlistSources.has(item.sourceId)
}

function showDateTag(item) {
  return Boolean(itemDateValue(item))
}

function showAuthorTag(item) {
  if (isAggregateList.value) return false
  if (item.author === item.sourceName) return false
  return Boolean(item.author)
}

function hasMetaTags(item) {
  return showSourceTag(item) || showDateTag(item) || showAuthorTag(item)
}

function showSummary(item) {
  return !hiddenSummarySources.has(item.sourceId) && Boolean(item.summary)
}

function showFundTags(item) {
  return item.sourceId !== 'gelonghui' && item.relatedFunds.length
}

function showScoreMark() {
  return isAggregateList.value || activeReport.value !== 'weekly'
}

function sourceStatusText(source) {
  if (source.status === 'ok') return `获取 ${source.fetched} 条`
  if (source.status === 'cached') return `缓存 ${source.fetched} 条`
  if (source.status === 'empty') return '暂无条目'
  if (source.status === 'skipped') return '待接入'
  if (source.status === 'rate_limited') return '已限流'
  return '异常'
}

function selectSource(sourceId) {
  activeSource.value = sourceId
  if (rankedHotlistSources.has(sourceId)) setReport('daily')
}

onMounted(() => load(false))
</script>

<template>
  <section class="news-surface">
    <header class="news-head">
      <p class="eyebrow"><Newspaper />持仓新闻</p>
      <div class="head-row">
        <div>
          <h1>持仓相关财经资讯</h1>
          <p>官方源优先，公开来源采集，过滤低相关短线噪音。</p>
        </div>
        <button class="primary-button" type="button" :disabled="state.loading" @click="load(true)">
          <RefreshCw />刷新
        </button>
      </div>
    </header>

    <div class="source-strip" aria-label="新闻源筛选">
      <button type="button" :class="['source-pill', { selected: activeSource === 'all' }]" @click="selectSource('all')">
        <strong>全部来源</strong>
        <small>聚合</small>
      </button>
      <button
        v-for="source in sourceSummary"
        :key="source.sourceId"
        type="button"
        :class="['source-pill', source.status, { selected: activeSource === source.sourceId }]"
        :title="source.reason || `${source.sourceName} 专有信息`"
        @click="selectSource(source.sourceId)"
      >
        <strong>{{ source.sourceName }}</strong>
        <small>{{ sourceStatusText(source) }}</small>
      </button>
    </div>

    <div v-if="state.loading" class="news-loading">
      <span></span><span></span><span></span>
    </div>
    <div v-else-if="state.error" class="news-empty error">
      <strong>{{ state.error }}</strong>
      <button class="text-button" type="button" @click="load(true)"><RefreshCw />重试</button>
    </div>
    <template v-else>
      <section class="bucket-tabs" aria-label="新闻筛选">
        <button type="button" :class="{ on: activeReport === 'weekly' }" @click="setReport('weekly')">周报</button>
        <button type="button" :class="{ on: activeReport === 'daily' }" @click="setReport('daily')">日报</button>
      </section>

      <section :class="['news-list', { 'aggregate-list': isAggregateList }]" :aria-label="activeListLabel">
        <article
          v-for="(item, index) in visibleItems"
          :key="item.id"
          :class="[
            'news-row',
            {
              'feed-row': isFeedStyle(item),
              'gelonghui-daily-row': item.sourceId === 'gelonghui' && activeReport === 'daily',
              'no-score-mark': !showScoreMark(),
            },
          ]"
        >
          <div v-if="showScoreMark()" class="score-mark">
            <strong>{{ isAggregateList ? index + 1 : isFeedStyle(item) ? index + 1 : item.totalScore }}</strong>
            <small>{{ isAggregateList || isFeedStyle(item) ? '' : '/10' }}</small>
          </div>
          <div class="news-copy">
            <h2>{{ item.title }}</h2>
            <p v-if="showSummary(item)">{{ item.summary }}</p>
            <div v-if="hasMetaTags(item)" class="meta-line">
              <span v-if="showSourceTag(item)">{{ item.sourceName }}</span>
              <span v-if="showDateTag(item)">{{ formatDateLabel(item) }}</span>
              <span v-if="showAuthorTag(item)">{{ item.author }}</span>
            </div>
            <div v-if="showFundTags(item)" class="fund-tags">
              <span v-for="fund in item.relatedFunds" :key="`${item.id}-${fund.name}`">
                {{ fund.name }}
              </span>
            </div>
          </div>
          <a class="icon-button" :href="item.url" target="_blank" rel="noreferrer" aria-label="打开原始来源">
            <ExternalLink />
          </a>
        </article>
        <p v-if="!visibleItems.length" class="news-empty">暂无{{ activeListLabel }}信息。</p>
      </section>

    </template>
  </section>
</template>

<style scoped>
.news-surface {
  display: grid;
  gap: 16px;
}

.news-head {
  display: grid;
  gap: 8px;
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  gap: 6px;
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
h2,
p {
  margin: 0;
}

h1 {
  font-size: 32px;
  line-height: 1.15;
}

.head-row {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
}

.head-row p {
  margin-top: 8px;
  color: var(--muted);
}

.source-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.source-pill {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--text);
  transition:
    background 160ms ease-out,
    border-color 160ms ease-out,
    color 160ms ease-out;
}

.source-pill strong {
  transition: color 160ms ease-out;
}

.source-pill:hover {
  border-color: var(--line-strong);
  background: var(--surface-soft);
}

.source-pill small {
  color: var(--muted);
  transition: color 160ms ease-out;
}

.source-pill.ok,
.source-pill.cached {
  border-color: var(--line);
  background: var(--surface);
}

.source-pill.error {
  border-color: color-mix(in oklch, var(--rise) 32%, var(--line));
  background: var(--rise-soft);
}

.source-pill.selected {
  border-color: color-mix(in oklch, var(--accent) 62%, var(--line));
  background: color-mix(in oklch, var(--accent-soft) 78%, var(--surface));
  color: var(--accent);
  box-shadow:
    inset 0 0 0 1px color-mix(in oklch, var(--accent) 18%, transparent),
    0 1px 2px rgba(30, 39, 52, 0.06);
}

.source-pill.selected:hover {
  border-color: color-mix(in oklch, var(--accent) 74%, var(--line));
  background: color-mix(in oklch, var(--accent-soft) 88%, var(--surface));
}

.source-pill.selected small {
  color: color-mix(in oklch, var(--accent) 72%, var(--muted));
}

.source-pill:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.source-pill.selected:focus-visible {
  box-shadow:
    inset 0 0 0 1px color-mix(in oklch, var(--accent) 22%, transparent),
    0 0 0 3px var(--accent-soft);
}

.bucket-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.bucket-tabs button {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--text);
}

.bucket-tabs button.on {
  border-color: var(--accent);
  background: var(--accent);
  color: oklch(98% 0.004 250);
}

.news-list {
  display: grid;
  gap: 10px;
}

.news-list.aggregate-list {
  gap: 0;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--surface);
}

.news-row {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr) 36px;
  gap: 12px;
  align-items: start;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--surface);
}

.news-row.feed-row {
  grid-template-columns: 40px minmax(0, 1fr) 36px;
  gap: 8px;
  padding: 16px 18px;
  border-radius: var(--radius-md);
}

.news-row.gelonghui-daily-row {
  grid-template-columns: 40px minmax(0, 1fr) 34px;
  gap: 10px;
  align-items: center;
  min-height: 54px;
  padding: 9px 16px;
}

.news-row.no-score-mark,
.news-row.feed-row.no-score-mark {
  grid-template-columns: minmax(0, 1fr) 36px;
  gap: 12px;
}

.news-list.aggregate-list .news-row {
  grid-template-columns: 40px minmax(0, 1fr) 36px;
  gap: 10px;
  align-items: start;
  min-height: 104px;
  padding: 17px 18px 16px;
  border: 0;
  border-bottom: 1px solid var(--line);
  border-radius: 0;
  background: var(--surface);
}

.news-list.aggregate-list .news-row:last-of-type {
  border-bottom: 0;
}

.score-mark {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface-soft);
}

.feed-row .score-mark {
  width: 28px;
  height: calc(16px * 1.35);
  border-color: transparent;
  background: transparent;
  color: oklch(58% 0.17 36);
}

.score-mark strong {
  font-size: 18px;
  line-height: 1;
}

.score-mark small {
  margin-top: -8px;
  color: var(--muted);
  font-size: 11px;
}

.feed-row .score-mark small {
  display: none;
}

.feed-row .score-mark strong {
  line-height: 1.35;
}

.gelonghui-daily-row .score-mark {
  width: 28px;
  height: 22px;
  align-self: center;
  place-items: center;
}

.gelonghui-daily-row .score-mark strong {
  line-height: 22px;
  transform: translateY(0.5px);
}

.gelonghui-daily-row .news-copy {
  display: flex;
  min-height: 34px;
  align-items: center;
}

.gelonghui-daily-row .news-copy h2 {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 22px;
  transform: translateY(0.5px);
}

.gelonghui-daily-row .icon-button {
  align-self: center;
  width: 34px;
  height: 34px;
  min-height: 34px;
}

.news-list.aggregate-list .score-mark {
  display: grid;
  width: 28px;
  height: auto;
  min-height: calc(16px * 1.35);
  place-items: start center;
  align-self: start;
  padding-top: 0;
  border-color: transparent;
  background: transparent;
  color: oklch(58% 0.17 36);
}

.news-list.aggregate-list .score-mark strong {
  font-size: 16px;
  line-height: 1.35;
  transform: none;
}

.news-list.aggregate-list .score-mark small {
  display: none;
}

.news-list.aggregate-list .news-copy {
  display: grid;
  min-height: 0;
  align-self: start;
  align-content: start;
  gap: 8px;
}

.news-list.aggregate-list .news-copy h2 {
  overflow: visible;
  text-overflow: clip;
  white-space: normal;
  line-height: 1.35;
  transform: none;
}

.news-list.aggregate-list .news-copy p {
  margin-top: 0;
  max-width: 88ch;
  color: var(--muted);
  line-height: 1.55;
}

.news-list.aggregate-list .icon-button {
  align-self: start;
  width: 34px;
  height: 34px;
  min-height: 34px;
}

.news-copy {
  min-width: 0;
}

.news-copy h2 {
  font-size: 16px;
  line-height: 1.35;
}

.news-copy p {
  margin-top: 6px;
  color: var(--muted);
}

.feed-row .news-copy p {
  max-width: 88ch;
  line-height: 1.55;
}

.meta-line,
.fund-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.meta-line span,
.fund-tags span {
  padding: 3px 7px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--surface-soft);
  color: var(--muted);
  font-size: 12px;
}

.fund-tags span {
  color: var(--accent);
}

.news-empty,
.news-loading {
  min-height: 160px;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--surface);
}

.news-empty {
  display: grid;
  place-items: center;
  color: var(--muted);
}

.news-empty.error {
  gap: 12px;
  color: var(--rise);
}

.news-loading {
  display: grid;
  gap: 10px;
  padding: 18px;
}

.news-loading span {
  height: 18px;
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, var(--surface-soft), var(--surface-pressed), var(--surface-soft));
  background-size: 220% 100%;
  animation: load 1.2s ease-out infinite;
}

@keyframes load {
  from { background-position: 100% 0; }
  to { background-position: -100% 0; }
}

@media (max-width: 760px) {
  .head-row {
    align-items: start;
    flex-direction: column;
  }

  .news-row {
    grid-template-columns: 48px minmax(0, 1fr);
  }

  .news-row .icon-button {
    grid-column: 2;
    width: fit-content;
    padding: 0 10px;
  }

  .news-list.aggregate-list .news-row {
    grid-template-columns: 34px minmax(0, 1fr) 34px;
    min-height: 96px;
    padding: 14px 12px;
  }

  .news-list.aggregate-list .icon-button {
    grid-column: auto;
    width: 34px;
    padding: 0;
  }
}
</style>
