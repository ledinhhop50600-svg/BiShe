<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import echarts from '@/utils/echarts'

/**
 * ECharts 容器：只负责初始化、更新与自适应，不掺业务逻辑。
 * 选项由父组件按主题色计算好后传入。
 */
const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '260px' },
})

const el = ref(null)
let chart = null
let observer = null

function render() {
  if (chart) {
    chart.setOption(props.option, true)
  }
}

onMounted(() => {
  chart = echarts.init(el.value)
  render()
  observer = new ResizeObserver(() => chart && chart.resize())
  observer.observe(el.value)
})

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  observer && observer.disconnect()
  chart && chart.dispose()
  chart = null
})
</script>

<template>
  <div ref="el" class="chart-box" :style="{ height }"></div>
</template>

<style scoped>
.chart-box {
  width: 100%;
}
</style>
