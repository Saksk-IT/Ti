<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  query?: string;
  text: string;
}>();

interface TextPart {
  highlighted: boolean;
  text: string;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

const parts = computed<TextPart[]>(() => {
  const terms = (props.query ?? '')
    .trim()
    .toLocaleLowerCase('zh-CN')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 4);
  if (!terms.length || !props.text) return [{ highlighted: false, text: props.text }];

  const pattern = new RegExp(`(${terms.map(escapeRegExp).join('|')})`, 'giu');
  return props.text.split(pattern).filter(Boolean).map((text) => ({
    highlighted: terms.includes(text.toLocaleLowerCase('zh-CN')),
    text,
  }));
});
</script>

<template>
  <template v-for="(part, index) in parts" :key="`${index}-${part.text}`">
    <mark v-if="part.highlighted" class="plaza-highlight">{{ part.text }}</mark>
    <template v-else>{{ part.text }}</template>
  </template>
</template>
