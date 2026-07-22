import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts'

export function useChart(optionRef) {
  const elRef = ref(null)
  const chartRef = shallowRef(null)
  let chart = null

  function render() {
    if (chart && optionRef.value) chart.setOption(optionRef.value, true)
  }

  function onResize() {
    if (chart) chart.resize()
  }

  onMounted(() => {
    chart = echarts.init(elRef.value)
    chartRef.value = chart
    render()
    window.addEventListener('resize', onResize)
  })

  watch(optionRef, render, { deep: true })

  onBeforeUnmount(() => {
    window.removeEventListener('resize', onResize)
    if (chart) chart.dispose()
    chartRef.value = null
  })

  return { elRef, chartRef }
}
