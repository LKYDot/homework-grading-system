<script setup lang="ts">
import { computed } from 'vue'
import type { GradingResult } from '@/api/homework'

const props = defineProps<{
  item: GradingResult
}>()

const resultClass = computed(() => {
  if (props.item.result === '正确') return 'result-correct'
  if (props.item.result === '部分正确') return 'result-partial'
  return 'result-incorrect'
})

const resultIcon = computed(() => {
  if (props.item.result === '正确') return 'check'
  if (props.item.result === '部分正确') return 'minus'
  return 'x'
})

const resultAriaLabel = computed(() => {
  return `第${props.item.question_no}题，得分${props.item.score}分（满分${props.item.max_score}分），${props.item.result}`
})
</script>

<template>
  <div class="grading-card" :class="resultClass" role="article" :aria-label="resultAriaLabel">
    <div class="gc-header">
      <span class="gc-qno">第 {{ item.question_no }} 题</span>
      <div style="display:flex;align-items:center;gap:6px;">
        <!-- result icon -->
        <svg v-if="resultIcon === 'check'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:18px;height:18px;color:var(--color-success);" aria-hidden="true">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        <svg v-else-if="resultIcon === 'minus'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:18px;height:18px;color:var(--color-warning);" aria-hidden="true">
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:18px;height:18px;color:var(--color-danger);" aria-hidden="true">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
        <span class="gc-score">
          {{ item.score }} <span class="gc-max">/ {{ item.max_score }}</span>
        </span>
      </div>
    </div>
    <div v-if="item.comment" class="gc-comment">{{ item.comment }}</div>
    <div v-if="item.analysis" class="gc-analysis">{{ item.analysis }}</div>
    <div v-if="item.confidence !== undefined" style="font-size:0.72rem;color:var(--color-text-muted);margin-top:8px;display:flex;align-items:center;gap:4px;">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;" aria-hidden="true">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
      </svg>
      置信度: {{ (item.confidence * 100).toFixed(0) }}%
    </div>
  </div>
</template>
