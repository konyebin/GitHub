<script setup lang="ts">
import { ref, watch, onMounted } from "vue";

const props = defineProps<{
  lines: string[];
  speed?: number;
}>();

const displayed = ref<string[]>([]);
const currentLine = ref(0);
const currentChar = ref(0);
const done = ref(false);

function typeNext() {
  if (currentLine.value >= props.lines.length) {
    done.value = true;
    return;
  }
  const line = props.lines[currentLine.value];
  if (currentChar.value < line.length) {
    if (currentChar.value === 0) {
      displayed.value.push("");
    }
    displayed.value[currentLine.value] += line[currentChar.value];
    currentChar.value++;
    setTimeout(typeNext, props.speed ?? 18);
  } else {
    currentLine.value++;
    currentChar.value = 0;
    setTimeout(typeNext, 80);
  }
}

watch(
  () => props.lines,
  () => {
    displayed.value = [];
    currentLine.value = 0;
    currentChar.value = 0;
    done.value = false;
    typeNext();
  },
  { immediate: false }
);

onMounted(() => typeNext());
</script>

<template>
  <div class="terminal-output">
    <div class="terminal-chrome">
      <span class="terminal-dot red" />
      <span class="terminal-dot yellow" />
      <span class="terminal-dot green" />
      <span class="terminal-title">terminal</span>
    </div>
    <div class="terminal-body">
      <div v-for="(line, i) in displayed" :key="i" class="terminal-line">
        <span v-if="i === 0" class="terminal-prompt">$ </span>{{ line }}
      </div>
      <span v-if="!done" class="terminal-cursor">▊</span>
    </div>
  </div>
</template>
