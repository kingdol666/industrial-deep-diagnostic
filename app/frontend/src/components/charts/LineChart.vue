<template>
  <div class="chart-wrapper" style="width:100%;height:100%;min-height:300px">
    <v-chart :option="chartOption" autoresize />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import VChart from 'vue-echarts';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { LineChart as ELineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, DataZoomComponent, LegendComponent } from 'echarts/components';

use([CanvasRenderer, ELineChart, GridComponent, TooltipComponent, DataZoomComponent, LegendComponent]);

const props = defineProps({
  data: { type: Array, default: () => [] },
  xField: { type: String, default: 'time' },
  yFields: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  colors: { type: Array, default: () => [] },
  zoomable: { type: Boolean, default: true },
});

const DEFAULT_COLORS = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4'];

const chartOption = computed(() => {
  const series = (props.yFields || []).map((field, idx) => ({
    name: field,
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    lineStyle: { width: 2 },
    data: (props.data || []).map((d) => d[field]),
    emphasis: { focus: 'series' },
  }));

  return {
    title: props.title ? { text: props.title, left: 'center' } : undefined,
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#ddd',
      borderWidth: 1,
      textStyle: { color: '#333' },
    },
    legend: {
      type: 'scroll',
      bottom: 0,
      icon: 'roundRect',
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: props.yFields.length > 1 ? '15%' : '10%',
      top: props.title ? '15%' : '8%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: (props.data || []).map((d) => d[props.xField]),
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#ccc' } },
      axisLabel: {
        color: '#666',
        rotate: (props.data || []).length > 20 ? 45 : 0,
      },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#eee', type: 'dashed' } },
      axisLabel: { color: '#666' },
    },
    color: props.colors.length ? props.colors : DEFAULT_COLORS,
    dataZoom: props.zoomable
      ? [
          { type: 'inside', start: 0, end: 100 },
          { type: 'slider', start: 0, end: 100, height: 20, bottom: 0 },
        ]
      : undefined,
    series,
  };
});
</script>

<style scoped>
.chart-wrapper {
  position: relative;
}
</style>
