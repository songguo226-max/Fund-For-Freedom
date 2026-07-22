<script setup>
import { computed, onBeforeUnmount, watch } from 'vue'
import { useChart } from '../../shared/charting/useChart'

const props = defineProps({
  indicator: { type: Object, required: true },
  compact: { type: Boolean, default: false },
  range: { type: String, default: 'all' },
})

const emit = defineEmits(['visible-range'])

const points = computed(() => props.indicator.points || [])
const chartColor = computed(() => props.indicator.color || '#005a9c')
const rangeIndexes = computed(() => computeRangeIndexes(points.value, props.range))
const isPolicyRate = computed(() => props.indicator.id === 'policy-rate')

const shortMonths = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function pointTime(point) {
  return new Date(`${point.date}T00:00:00Z`).getTime()
}

function computeRangeIndexes(items, range) {
  const lastIndex = Math.max(items.length - 1, 0)
  if (props.compact || range === 'all' || items.length < 2) {
    return { startIndex: 0, endIndex: lastIndex }
  }
  const latest = new Date(items.at(-1).date)
  const start = new Date(latest)
  if (range === 'ytd') {
    start.setMonth(0, 1)
  } else {
    const months = { '1m': 1, '3m': 3, '6m': 6, '1y': 12 }[range] || 0
    start.setMonth(start.getMonth() - months)
  }
  const startIndex = Math.max(items.findIndex((item) => new Date(item.date) >= start), 0)
  return { startIndex, endIndex: lastIndex }
}

function formatTooltipValue(point) {
  if (!point) return ''
  if (props.indicator.chartType === 'range') {
    return `${point.lower?.toFixed(2)}% - ${point.upper?.toFixed(2)}%`
  }
  const sign = props.indicator.id === 'gdp' && point.value > 0 ? '+' : ''
  return `${sign}${Number(point.value).toFixed(1)}%`
}

function axisLabel(label) {
  if (!label) return ''
  if (props.compact) {
    const year = String(label).match(/\b(20\d{2})\b/)?.[1]
    return year || label
  }
  if (props.indicator.id === 'inflation') {
    if (!String(label).startsWith('January ')) return ''
    return String(label).match(/\b(20\d{2})\b/)?.[1] || label
  }
  if (props.indicator.id === 'unemployment') {
    if (!String(label).startsWith('January ')) return ''
    return String(label).match(/\b(20\d{2})\b/)?.[1] || label
  }
  if (props.indicator.id === 'gdp') return label.replace(' ', '\n')
  return label.replace(' ', '\n')
}

function policyAxisLabel(value) {
  const day = new Date(value)
  if (Number.isNaN(day.getTime())) return ''
  return `${shortMonths[day.getUTCMonth()]}'${String(day.getUTCFullYear()).slice(2)}`
}

function seriesPoint(point, value) {
  return {
    value: isPolicyRate.value ? [pointTime(point), value] : value,
    point,
  }
}

const option = computed(() => {
  const labels = points.value.map((point) => point.label)
  const startPoint = points.value[rangeIndexes.value.startIndex]
  const endPoint = points.value[rangeIndexes.value.endIndex]
  const startZoomValue = isPolicyRate.value && startPoint ? pointTime(startPoint) : labels[rangeIndexes.value.startIndex]
  const endZoomValue = isPolicyRate.value && endPoint ? pointTime(endPoint) : labels[rangeIndexes.value.endIndex]
  const policyMin = isPolicyRate.value && points.value[0] ? pointTime(points.value[0]) : undefined
  const policyMax = isPolicyRate.value && points.value.at(-1) ? pointTime(points.value.at(-1)) : undefined
  const common = {
    animationDuration: props.compact ? 250 : 380,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: props.indicator.chartType === 'bar' ? 'shadow' : 'line' },
      formatter(params) {
        const point = params?.[0]?.data?.point
        if (!point) return ''
        return [
          `<div class="fed-tooltip-date">${point.label}</div>`,
          `<div class="fed-tooltip-row"><span>${props.indicator.title}</span><strong>${formatTooltipValue(point)}</strong></div>`,
        ].join('')
      },
    },
    grid: props.compact
      ? { top: 8, right: 10, bottom: 28, left: 34 }
      : isPolicyRate.value
        ? { top: 18, right: 62, bottom: 82, left: 46 }
        : { top: 18, right: 62, bottom: 78, left: 40 },
    xAxis: {
      type: isPolicyRate.value ? 'time' : 'category',
      data: isPolicyRate.value ? undefined : labels,
      min: policyMin,
      max: policyMax,
      splitNumber: isPolicyRate.value ? 10 : undefined,
      boundaryGap: isPolicyRate.value ? false : props.indicator.chartType === 'bar',
      axisTick: { show: !props.compact },
      axisLine: { lineStyle: { color: '#263238' } },
      axisLabel: {
        color: '#1f2933',
        hideOverlap: true,
        rotate: props.compact ? 0 : 38,
        formatter: isPolicyRate.value ? policyAxisLabel : axisLabel,
        fontSize: props.compact ? 10 : 11,
      },
    },
    yAxis: {
      type: 'value',
      name: props.compact ? '' : props.indicator.unit,
      nameLocation: 'middle',
      nameGap: 42,
      position: props.compact ? 'left' : 'right',
      splitLine: { lineStyle: { color: '#dfe4e8' } },
      axisLine: { show: !props.compact, lineStyle: { color: '#263238' } },
      axisLabel: { color: '#1f2933', fontSize: props.compact ? 10 : 11 },
    },
    dataZoom: props.compact
      ? []
      : [
          {
            type: 'slider',
            bottom: 8,
            height: 30,
            startValue: startZoomValue,
            endValue: endZoomValue,
            borderColor: '#b7c0cb',
            fillerColor: 'rgba(55, 91, 170, 0.18)',
            handleSize: 12,
            showDetail: false,
          },
          { type: 'inside', startValue: startZoomValue, endValue: endZoomValue },
        ],
  }

  if (props.indicator.chartType === 'bar') {
    return {
      ...common,
      series: [
        {
          name: props.indicator.title,
          type: 'bar',
          barMaxWidth: props.compact ? 5 : 13,
          data: points.value.map((point) => ({ value: point.value, point })),
          itemStyle: { color: chartColor.value },
        },
      ],
    }
  }

  if (props.indicator.chartType === 'range') {
    return {
      ...common,
      yAxis: { ...common.yAxis, min: 0 },
      series: [
        {
          name: 'Lower target',
          type: 'line',
          step: 'end',
          showSymbol: false,
          data: points.value.map((point) => seriesPoint(point, point.lower)),
          lineStyle: { width: props.compact ? 2 : 4, color: chartColor.value },
          itemStyle: { color: chartColor.value },
        },
        {
          name: 'Upper target',
          type: 'line',
          step: 'end',
          showSymbol: false,
          data: points.value.map((point) => seriesPoint(point, point.upper)),
          lineStyle: { width: props.compact ? 2 : 4, color: chartColor.value },
          areaStyle: { color: 'rgba(115, 137, 74, 0.22)' },
          itemStyle: { color: chartColor.value },
        },
      ],
    }
  }

  return {
    ...common,
    series: [
      {
        name: props.indicator.title,
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: points.value.map((point) => ({ value: point.value, point })),
        lineStyle: { width: props.compact ? 2 : 3, color: chartColor.value },
        itemStyle: { color: chartColor.value },
      },
    ],
  }
})

function clampIndex(value) {
  return Math.max(0, Math.min(points.value.length - 1, value))
}

function nearestPointIndexByTime(value) {
  const target = Number(value)
  if (!Number.isFinite(target)) return -1
  let bestIndex = 0
  let bestDistance = Infinity
  points.value.forEach((point, index) => {
    const distance = Math.abs(pointTime(point) - target)
    if (distance < bestDistance) {
      bestDistance = distance
      bestIndex = index
    }
  })
  return bestIndex
}

function indexFromZoomValue(value, percent) {
  const labels = points.value.map((point) => point.label)
  if (typeof value === 'string') {
    const index = labels.indexOf(value)
    if (index >= 0) return index
  }
  if (Number.isFinite(value)) {
    if (isPolicyRate.value) return clampIndex(nearestPointIndexByTime(value))
    return clampIndex(Math.round(value))
  }
  if (Number.isFinite(percent) && points.value.length > 1) {
    return clampIndex(Math.round((percent / 100) * (points.value.length - 1)))
  }
  return 0
}

function emitVisibleRange(startIndex, endIndex) {
  const start = points.value[clampIndex(startIndex)]
  const end = points.value[clampIndex(endIndex)]
  if (!start || !end || props.compact) return
  emit('visible-range', {
    indicatorId: props.indicator.id,
    start,
    end,
  })
}

function handleDataZoom(params) {
  const zoom = params?.batch?.[0] || params || {}
  const startIndex = indexFromZoomValue(zoom.startValue, zoom.start)
  const endIndex = indexFromZoomValue(zoom.endValue, zoom.end)
  emitVisibleRange(startIndex, endIndex)
}

const { elRef, chartRef } = useChart(option)
let attachedChart = null

watch(chartRef, (chart) => {
  if (attachedChart) attachedChart.off('dataZoom', handleDataZoom)
  attachedChart = chart
  if (attachedChart && !props.compact) attachedChart.on('dataZoom', handleDataZoom)
})

watch(rangeIndexes, ({ startIndex, endIndex }) => {
  emitVisibleRange(startIndex, endIndex)
}, { immediate: true })

onBeforeUnmount(() => {
  if (attachedChart) attachedChart.off('dataZoom', handleDataZoom)
})
</script>

<template>
  <div ref="elRef" :class="['fed-chart', { compact }]"></div>
</template>

<style scoped>
.fed-chart {
  width: 100%;
  height: 430px;
}

.fed-chart.compact {
  height: 176px;
}

:global(.fed-tooltip-date) {
  margin-bottom: 6px;
  color: #002b49;
  font-size: 12px;
}

:global(.fed-tooltip-row) {
  display: grid;
  grid-template-columns: minmax(112px, 1fr) auto;
  gap: 12px;
  align-items: center;
  color: #263238;
  font-size: 12px;
}

:global(.fed-tooltip-row strong) {
  color: #2d6297;
}

@media (max-width: 720px) {
  .fed-chart {
    height: 360px;
  }

  .fed-chart.compact {
    height: 150px;
  }
}
</style>
