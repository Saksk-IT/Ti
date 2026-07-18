<script setup lang="ts">
import { computed } from 'vue';

export type AsyncStateMode = 'loading' | 'empty' | 'error';

const props = defineProps<{
  message?: string;
  mode: AsyncStateMode;
  requestId?: string;
  title?: string;
}>();

const emit = defineEmits<{
  retry: [];
}>();

const defaultTitle = computed(() => {
  if (props.mode === 'loading') return '正在读取公共题库';
  if (props.mode === 'empty') return '没有找到符合条件的题库';
  return '暂时无法读取内容';
});

const defaultMessage = computed(() => {
  if (props.mode === 'loading') return '请稍候，正在请求只读目录。';
  if (props.mode === 'empty') return '可以清空关键词或调整板块与排序条件。';
  return '请稍后重试；如持续失败，可提供下方请求 ID。';
});
</script>

<template>
  <section
    class="async-state"
    :class="`async-state--${mode}`"
    :aria-busy="mode === 'loading'"
    :aria-live="mode === 'loading' ? 'polite' : 'assertive'"
  >
    <div v-if="mode === 'loading'" class="async-state__skeleton" aria-hidden="true">
      <span></span><span></span><span></span>
    </div>
    <div v-else class="async-state__symbol" aria-hidden="true">
      {{ mode === 'empty' ? '○' : '!' }}
    </div>
    <h2>{{ title ?? defaultTitle }}</h2>
    <p>{{ message ?? defaultMessage }}</p>
    <p v-if="requestId" class="request-id-inline">请求 ID：{{ requestId }}</p>
    <button v-if="mode === 'error'" class="button button--secondary" type="button" @click="emit('retry')">
      重新加载
    </button>
  </section>
</template>
