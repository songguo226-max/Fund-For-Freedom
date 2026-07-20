import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

export function useChart(optionRef) {
  const elRef = ref(null)
  let chart = null

  function render() {
    if (chart && optionRef.value) chart.setOption(optionRef.value, true)
  }

  function onResize() {
    if (chart) chart.resize()
  }

  onMounted(() => {
    chart = echarts.init(elRef.value)
    render()
    window.addEventListener('resize', onResize)
  })

  watch(optionRef, render, { deep: true })

  onBeforeUnmount(() => {
    window.removeEventListener('resize', onResize)
    if (chart) chart.dispose()
  })

  return { elRef }
}
