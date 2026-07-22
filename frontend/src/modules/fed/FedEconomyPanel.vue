<script setup>
import { ArrowRight, Landmark, RefreshCw } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../../integrations/fund-api'
import FedEconomyChart from './FedEconomyChart.vue'

const state = reactive({ loading: false, error: '', data: null })
const activeDetail = ref('policy-rate')
const selectedZoom = ref('all')
const visibleRange = ref({ indicatorId: '', start: null, end: null })

const indicators = computed(() => state.data?.indicators || [])
const activeIndicator = computed(() => (
  indicators.value.find((item) => item.id === activeDetail.value) || indicators.value[0]
))
const visibleDateRange = computed(() => {
  const indicator = activeIndicator.value
  if (!indicator) return ''
  const range = visibleRange.value.indicatorId === indicator.id
    ? visibleRange.value
    : { start: indicator.points[0], end: indicator.points.at(-1) }
  if (!range.start || !range.end) return ''
  return `${formatRangeDate(indicator, range.start)} -> ${formatRangeDate(indicator, range.end)}`
})

const zoomOptions = computed(() => {
  if (activeIndicator.value?.id === 'policy-rate') {
    return [
      { value: '1m', label: '1m' },
      { value: '3m', label: '3m' },
      { value: '6m', label: '6m' },
      { value: 'ytd', label: 'YTD' },
      { value: '1y', label: '1y' },
      { value: 'all', label: 'All' },
    ]
  }
  return [
    { value: '6m', label: '6m' },
    { value: 'ytd', label: 'YTD' },
    { value: '1y', label: '1y' },
    { value: 'all', label: 'All' },
  ]
})

async function load() {
  state.loading = true
  state.error = ''
  try {
    state.data = await api.fedEconomyAtGlance()
    if (!indicators.value.some((item) => item.id === activeDetail.value)) {
      activeDetail.value = indicators.value[0]?.id || 'policy-rate'
    }
  } catch (error) {
    state.error = error.message || 'Federal Reserve data failed to load'
  } finally {
    state.loading = false
  }
}

function showDetail(id) {
  activeDetail.value = id
  selectedZoom.value = 'all'
  visibleRange.value = { indicatorId: '', start: null, end: null }
}

function detailMeasure(indicator) {
  if (indicator?.id === 'inflation') return 'Percent change from year earlier'
  if (indicator?.id === 'gdp') return 'Percent change from the previous quarter'
  return ''
}

function setVisibleRange(range) {
  visibleRange.value = range
}

const shortMonths = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function utcDate(value) {
  return new Date(`${value}T00:00:00Z`)
}

function formatRangeDate(indicator, point) {
  if (indicator.id === 'gdp') return point.label
  const day = utcDate(point.date)
  const month = shortMonths[day.getUTCMonth()]
  const year = day.getUTCFullYear()
  if (indicator.id === 'policy-rate') return `${month} ${day.getUTCDate()} ${year}`
  return `${month} ${year}`
}

watch(activeDetail, () => {
  selectedZoom.value = 'all'
  visibleRange.value = { indicatorId: '', start: null, end: null }
})

onMounted(load)
</script>

<template>
  <section class="fed-surface">
    <header class="fed-head">
      <p class="eyebrow"><Landmark />Federal Reserve</p>
      <div class="head-row">
        <div>
          <h1>Economy at a Glance</h1>
          <p>Policy rate, inflation, unemployment, and GDP from Federal Reserve public data pages.</p>
        </div>
        <button class="text-button" type="button" :disabled="state.loading" @click="load">
          <RefreshCw />Refresh
        </button>
      </div>
    </header>

    <div v-if="state.loading" class="fed-loading">
      <span></span><span></span><span></span>
    </div>
    <div v-else-if="state.error" class="fed-empty error">
      <strong>{{ state.error }}</strong>
      <button class="text-button" type="button" @click="load"><RefreshCw />Retry</button>
    </div>
    <template v-else-if="state.data">
      <section class="fed-overview" aria-label="Economy at a Glance">
        <article
          v-for="indicator in indicators"
          :key="indicator.id"
          :class="['fed-card', { selected: activeDetail === indicator.id, policy: indicator.id === 'policy-rate' }]"
        >
          <h2>{{ indicator.title }}</h2>
          <template v-if="indicator.id === 'policy-rate'">
            <div class="policy-box">
              <p>{{ indicator.description }}</p>
              <strong>{{ indicator.latestDisplay }}</strong>
            </div>
          </template>
          <template v-else>
            <p class="metric-line"><strong>{{ indicator.latestDisplay }}</strong> {{ indicator.latestLabel }}</p>
            <FedEconomyChart :indicator="indicator" compact />
            <p class="source-line">Source: {{ indicator.source }}</p>
          </template>
          <button class="view-more" type="button" @click="showDetail(indicator.id)">
            View More <ArrowRight />
          </button>
        </article>
      </section>

      <section v-if="activeIndicator" class="fed-detail" aria-label="Economy at a Glance detail">
        <div class="detail-title-row">
          <h2>Economy at a Glance - {{ activeIndicator.title }}</h2>
          <a :href="activeIndicator.pageUrl" target="_blank" rel="noreferrer">Share</a>
        </div>

        <nav class="fed-metric-tabs" aria-label="Federal Reserve indicators">
          <button
            v-for="indicator in indicators"
            :key="indicator.id"
            type="button"
            :class="{ on: activeDetail === indicator.id }"
            @click="showDetail(indicator.id)"
          >
            {{ indicator.title }}
          </button>
        </nav>

        <div :class="['detail-grid', { 'policy-detail': activeIndicator.id === 'policy-rate' }]">
          <section class="detail-chart-panel">
            <h3>{{ activeIndicator.detailTitle }}</h3>
            <div class="zoom-row">
              <span>Zoom</span>
              <button
                v-for="option in zoomOptions"
                :key="option.value"
                type="button"
                :class="{ on: selectedZoom === option.value }"
                @click="selectedZoom = option.value"
              >
                {{ option.label }}
              </button>
              <p>{{ visibleDateRange }}</p>
            </div>
            <FedEconomyChart
              :indicator="activeIndicator"
              :range="selectedZoom"
              @visible-range="setVisibleRange"
            />
          </section>

          <aside class="detail-info-card">
            <h3>{{ activeIndicator.cardTitle }}</h3>
            <p>{{ activeIndicator.description }}</p>
            <small v-if="detailMeasure(activeIndicator)">{{ detailMeasure(activeIndicator) }}</small>
            <strong>{{ activeIndicator.latestDisplay }}</strong>
            <p>Latest Data: {{ activeIndicator.latestLabel }}</p>
            <a :href="activeIndicator.sourceUrl" target="_blank" rel="noreferrer">
              Source: {{ activeIndicator.source }}
            </a>
          </aside>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.fed-surface,
.fed-head {
  display: grid;
  gap: 16px;
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
h3,
p {
  margin: 0;
}

.head-row {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
}

.head-row h1,
.detail-title-row h2 {
  color: #002b49;
  font-family: var(--font-display);
  font-weight: 500;
}

.head-row h1 {
  font-size: 34px;
  line-height: 1.12;
}

.head-row p {
  margin-top: 8px;
  color: var(--muted);
}

.fed-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  padding: 12px;
  background: oklch(97.2% 0.004 250);
}

.fed-card {
  display: grid;
  min-width: 0;
  align-content: start;
  gap: 8px;
  padding: 10px 12px 12px;
  border-top: 4px solid transparent;
  background: oklch(99.3% 0.003 250);
}

.fed-card.policy {
  border: 1px solid #c6ced8;
  border-top: 4px solid #6e4078;
}

.fed-card h2 {
  color: #002b49;
  font-size: 17px;
  line-height: 1.25;
}

.policy-box {
  display: grid;
  min-height: 176px;
  align-content: start;
  gap: 22px;
  padding: 10px 16px;
}

.policy-box p,
.detail-info-card h3 {
  border-bottom: 1px solid #21415f;
  color: #002b49;
  font-family: var(--font-display);
  font-size: 18px;
  line-height: 1.35;
}

.policy-box strong,
.metric-line strong,
.detail-info-card strong {
  color: #356ca4;
  font-family: var(--font-display);
}

.policy-box strong {
  font-size: 30px;
}

.metric-line {
  color: #5c6670;
}

.metric-line strong {
  margin-right: 6px;
  font-size: 21px;
}

.source-line {
  color: #002b49;
  font-size: 12px;
}

.view-more {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  justify-self: end;
  gap: 5px;
  margin-top: auto;
  border: 0;
  background: transparent;
  color: #005ea8;
}

.view-more svg {
  width: 18px;
  height: 18px;
  padding: 3px;
  border-radius: 999px;
  background: #356ca4;
  color: oklch(98% 0.004 250);
}

.fed-detail {
  display: grid;
  gap: 12px;
  padding: 12px;
  background: var(--surface);
  border: 1px solid var(--line);
}

.detail-title-row {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid #b9c0c8;
}

.detail-title-row h2 {
  font-size: 30px;
  line-height: 1.12;
}

.detail-title-row a {
  color: #3c4651;
  text-decoration: none;
}

.fed-metric-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  border-bottom: 1px solid #cbd2da;
}

.fed-metric-tabs button {
  padding: 0 0 8px;
  border: 0;
  background: transparent;
  color: #005ea8;
}

.fed-metric-tabs button.on {
  color: #002b49;
  font-weight: 820;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 28px;
  align-items: start;
}

.detail-grid.policy-detail {
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 24px;
}

.detail-chart-panel {
  min-width: 0;
  padding: 8px 10px 0;
}

.policy-detail .detail-chart-panel {
  padding: 6px 0 0;
}

.detail-chart-panel h3 {
  margin-bottom: 22px;
  text-align: center;
  font-size: 19px;
}

.policy-detail .detail-chart-panel h3 {
  margin-bottom: 20px;
  color: #17212b;
  font-size: 20px;
  font-weight: 760;
}

.zoom-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  color: #4b5563;
  font-size: 12px;
}

.policy-detail .zoom-row {
  margin-bottom: 4px;
}

.zoom-row button {
  min-height: 24px;
  padding: 0 8px;
  border: 0;
  border-radius: 2px;
  background: #f1f4f8;
  color: #002b49;
}

.zoom-row button.on {
  background: #e7ecff;
  color: #001e7c;
  font-weight: 820;
}

.zoom-row p {
  margin-left: auto;
  color: #264cff;
}

.detail-info-card {
  display: grid;
  gap: 14px;
  padding: 14px 16px 18px;
  border: 1px solid #c6ced8;
  border-top: 4px solid #006fc9;
  background: #fbfcfd;
}

.policy-detail .detail-info-card {
  border-top-color: #6e4078;
  padding-bottom: 20px;
}

.detail-info-card p,
.detail-info-card small,
.detail-info-card a {
  color: #25313d;
  line-height: 1.45;
}

.detail-info-card strong {
  font-size: 31px;
  line-height: 1.05;
}

.detail-info-card a {
  color: #005ea8;
  text-decoration: none;
}

.fed-loading,
.fed-empty {
  min-height: 240px;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--surface);
}

.fed-loading {
  display: grid;
  gap: 10px;
  padding: 18px;
}

.fed-loading span {
  height: 22px;
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, var(--surface-soft), var(--surface-pressed), var(--surface-soft));
  background-size: 220% 100%;
  animation: load 1.2s ease-out infinite;
}

.fed-empty {
  display: grid;
  place-items: center;
  color: var(--muted);
}

.fed-empty.error {
  gap: 12px;
  color: var(--rise);
}

@keyframes load {
  from { background-position: 100% 0; }
  to { background-position: -100% 0; }
}

@media (max-width: 1160px) {
  .fed-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .detail-grid,
  .detail-grid.policy-detail {
    grid-template-columns: 1fr;
  }

  .detail-info-card {
    max-width: none;
  }
}

@media (max-width: 680px) {
  .head-row,
  .detail-title-row {
    align-items: start;
    flex-direction: column;
  }

  .fed-overview {
    grid-template-columns: 1fr;
    padding: 0;
    background: transparent;
  }

  .detail-title-row h2 {
    font-size: 25px;
  }

  .zoom-row p {
    width: 100%;
    margin-left: 0;
  }
}
</style>
