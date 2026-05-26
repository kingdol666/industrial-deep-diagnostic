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
import { HeatmapChart as EHeatmap } from 'echarts/charts';
import { GridComponent, TooltipComponent, VisualMapComponent } from 'echarts/components';

use([CanvasRenderer, EHeatmap, GridComponent, TooltipComponent, VisualMapComponent]);

const props = defineProps({
  data: { type: Array, default: () => [] },
  xLabels: { type: Array, default: () => [] },
  yLabels: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 1 },
});

const chartOption = computed(() => {
  const xData = props.xLabels.length ? props.xLabels : [...new Set((props.data || []).map((d) => d.x))];
  const yData = props.yLabels.length ? props.yLabels : [...new Set((props.data || []).map((d) => d.y))];
  const values = (props.data || []).map((d) => [xData.indexOf(d.x), yData.indexOf(d.y), d.value]);

  return {
    title: props.title ? { text: props.title, left: 'center' } : undefined,
    tooltip: {
      position: 'top',
      formatter: (params) => {
        const x = xData[params.value[0]];
        const y = yData[params.value[1]];
        const v = params.value[2];
        return `${x} × ${y}<br/>Value: ${typeof v === 'number' ? v.toFixed(4) : v}`;
      },
    },
    grid: {
      left: '8%',
      right: '12%',
      bottom: '12%',
      top: props.title ? '15%' : '8%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: xData,
      splitArea: { show: true },
      axisLine: { lineStyle: { color: '#ccc' } },
      axisLabel: {
        color: '#666',
        rotate: xData.length > 10 ? 45 : 0,
      },
    },
    yAxis: {
      type: 'category',
      data: yData,
      splitArea: { show: true },
      axisLine: { show: false },
      axisLabel: { color: '#666' },
    },
    visualMap: {
      min: props.min,
      max: props.max,
      calculable: true,
      orient: 'vertical',
      right: 0,
      top: 'center',
      inRange: {
        color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#fdae61', '#f46d43', '#d73027'],
      },
      textStyle: { color: '#666' },
    },
    series: [
      {
        type: 'heatmap',
        data: values,
        label: {
          show: xData.length <= 15 && yData.length <= 15,
          color: '#333',
          fontSize: 11,
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' },
        },
      },
    ],
  };
});
</script>

<style scoped>
.chart-wrapper {
  position: relative;
}
</style>
