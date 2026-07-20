<script setup>
import { computed } from 'vue'
import { useChart } from '../../shared/charting/useChart'

const props = defineProps({ points: { type: Array, default: () => [] } })
const ACCENT = '#3452b4'
const GOLD = '#b98a2e'

const option = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['单位净值', '累计净值'], top: 0 },
  grid: { top: 42, left: 54, right: 20, bottom: 38 },
  xAxis: { type: 'category', data: props.points.map((p) => p.date) },
  yAxis: { type: 'value', scale: true },
  series: [
    {
      name: '单位净值',
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: props.points.map((p) => p.nav),
      itemStyle: { color: ACCENT },
      lineStyle: { color: ACCENT },
    },
    {
      name: '累计净值',
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: props.points.map((p) => p.cumulativeNav),
      itemStyle: { color: GOLD },
      lineStyle: { color: GOLD },
    },
  ],
}))

const { elRef } = useChart(option)
</script>

<template><div ref="elRef" class="chart"></div></template>

<style scoped>
.chart { width: 100%; height: 360px; }
</style>
