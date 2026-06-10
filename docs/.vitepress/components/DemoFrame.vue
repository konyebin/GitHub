<script setup lang="ts">
import { ref } from "vue";

const props = defineProps<{
  src: string;
  height?: string;
  title?: string;
}>();

const loading = ref(true);
const error = ref(false);

function onLoad() {
  loading.value = false;
}

function onError() {
  loading.value = false;
  error.value = true;
}
</script>

<template>
  <div class="demo-frame" :style="{ '--frame-height': height ?? '420px' }">
    <div v-if="title" class="demo-frame-title">{{ title }}</div>
    <div class="demo-frame-viewport">
      <div v-if="loading" class="demo-frame-loading">Loading demo…</div>
      <div v-if="error" class="demo-frame-error">Demo failed to load.</div>
      <iframe
        :src="src"
        :title="title ?? 'Demo'"
        sandbox="allow-scripts allow-same-origin"
        @load="onLoad"
        @error="onError"
      />
    </div>
  </div>
</template>
