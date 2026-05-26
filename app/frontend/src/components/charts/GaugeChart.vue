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
import { GaugeChart as EGauge } from 'echarts/charts';

use([CanvasRenderer, EGauge]);

const props = defineProps({
  value: { type: Number, default: 0 },
  title: { type: String, default: '' },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  unit: { type: String, default: '' },
});

const chartOption = computed(() => {
  const range = props.max - props.min;
  const midLow = props.min + range * 0.3;
  const midHigh = props.min + range * 0.7;

  return {
    series: [
      {
        type: 'gauge',
        center: ['50%', '55%'],
        radius: '85%',
        startAngle: 220,
        endAngle: -40,
        min: props.min,
        max: props.max,
        splitNumber: 5,
        progress: {
          show: true,
          width: 12,
        },
        axisLine: {
          lineStyle: {
            width: 12,
            color: [
              [0.3, '#e74c3c'],
              [0.7, '#f39c12'],
              [1, '#27ae60'],
            ],
          },
        },
        axisTick: {
          show: false,
        },
        splitLine: {
          length: 8,
          lineStyle: { width: 2, color: '#999' },
        },
        axisLabel: {
          distance: 20,
          color: '#999',
          fontSize: 11,
          formatter: (v) => {
            if (Number.isInteger(v)) return v.toString();
            return v.toFixed(1);
          },
        },
        pointer: {
          width: 4,
          length: '65%',
          itemStyle: { color: '#333' },
        },
        detail: {
          valueAnimation: true,
          formatter: (v) => {
            const val = typeof v === 'number' ? v.toFixed(1) : v;
            return props.unit ? `${val} ${props.unit}` : `${val}`;
          },
          color: '#333',
          fontSize: 20,
          fontWeight: 'bold',
          offsetCenter: [0, '40%'],
        },
        title: {
          show: !!props.title,
          offsetCenter: [0, '70%'],
          fontSize: 14,
          color: '#666',
        },
        data: [
          {
            value: props.value,
            name: props.title,
          },
        ],
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
