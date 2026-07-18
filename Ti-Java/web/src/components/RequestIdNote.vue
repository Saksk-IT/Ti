<script setup lang="ts">
defineProps<{
  requestId?: string;
}>();
</script>

<template>
  <p v-if="requestId" class="request-id-note">
    <span aria-hidden="true">✓</span>
    请求 ID：<code>{{ requestId }}</code>。反馈问题时提供此 ID，可帮助定位请求。
  </p>
</template>
