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
import { ScatterChart as EScatter } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components';

use([CanvasRenderer, EScatter, GridComponent, TooltipComponent, LegendComponent]);

const props = defineProps({
  data: { type: Array, default: () => [] },
  xField: { type: String, default: 'x' },
  yField: { type: String, default: 'y' },
  xLabel: { type: String, default: '' },
  yLabel: { type: String, default: '' },
  title: { type: String, default: '' },
});

const chartOption = computed(() => {
  const xData = (props.data || []).map((d) => d[props.xField]);
  const yData = (props.data || []).map((d) => d[props.yField]);

  const allVals = [...xData, ...yData].filter((v) => typeof v === 'number');
  const xMin = Math.min(...xData);
  const xMax = Math.max(...xData);
  const yMin = Math.min(...yData);
  const yMax = Math.max(...yData);
  const xPad = (xMax - xMin) * 0.05 || 1;
  const yPad = (yMax - yMin) * 0.05 || 1;

  return {
    title: props.title ? { text: props.title, left: 'center' } : undefined,
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const x = params.data[0];
        const y = params.data[1];
        const labelX = props.xLabel || props.xField;
        const labelY = props.yLabel || props.yField;
        return `${labelX}: ${typeof x === 'number' ? x.toFixed(4) : x}<br/>${labelY}: ${typeof y === 'number' ? y.toFixed(4) : y}`;
      },
    },
    grid: {
      left: '10%',
      right: '8%',
      bottom: '12%',
      top: props.title ? '15%' : '8%',
      containLabel: true,
    },
    xAxis: {
      name: props.xLabel || props.xField,
      type: 'value',
      min: xMin - xPad,
      max: xMax + xPad,
      axisLine: { lineStyle: { color: '#ccc' } },
      splitLine: { lineStyle: { color: '#eee', type: 'dashed' } },
      axisLabel: { color: '#666' },
      nameTextStyle: { color: '#666', fontWeight: 'bold' },
    },
    yAxis: {
      name: props.yLabel || props.yField,
      type: 'value',
      min: yMin - yPad,
      max: yMax + yPad,
      axisLine: { lineStyle: { color: '#ccc' } },
      splitLine: { lineStyle: { color: '#eee', type: 'dashed' } },
      axisLabel: { color: '#666' },
      nameTextStyle: { color: '#666', fontWeight: 'bold' },
    },
    series: [
      {
        type: 'scatter',
        data: (props.data || []).map((d) => [d[props.xField], d[props.yField]]),
        symbolSize: 8,
        itemStyle: {
          color: '#5470c6',
          borderColor: '#fff',
          borderWidth: 1,
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(84,112,198,0.5)',
          },
          label: {
            show: true,
            formatter: (params) => `(${params.data[0].toFixed(2)}, ${params.data[1].toFixed(2)})`,
            position: 'top',
            fontSize: 11,
          },
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
