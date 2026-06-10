<script setup lang="ts">
import { ref } from "vue";
import TerminalOutput from "../TerminalOutput.vue";

const prompt = ref("Summarize the key benefits of RAG for enterprise search. Return JSON with title, bullets, and confidence score.");
const running = ref(false);
const outputKey = ref(0);
const outputLines = ref<string[]>([]);

const sampleResponse = `{
  "title": "RAG Benefits for Enterprise Search",
  "bullets": [
    "Grounds LLM responses in private company documents",
    "Reduces hallucination by retrieving relevant context first",
    "Enables up-to-date answers without retraining the model",
    "Supports citation of source documents for audit trails"
  ],
  "confidence": 0.92,
  "model": "gpt-4o-mini",
  "tokens_used": 847
}`;

function runPrompt() {
  if (running.value || !prompt.value.trim()) return;
  running.value = true;
  outputLines.value = ["Processing prompt…", "Retrieving context from vector store…", "Generating structured response…"];
  outputKey.value++;

  setTimeout(() => {
    outputLines.value = sampleResponse.split("\n");
    outputKey.value++;
    running.value = false;
  }, 2000);
}
</script>

<template>
  <div class="demo-genai">
    <label class="demo-genai-label">Prompt</label>
    <textarea v-model="prompt" class="demo-genai-prompt" rows="3" />
    <button class="demo-btn primary" :disabled="running" @click="runPrompt">
      {{ running ? "Running…" : "Run (simulated)" }}
    </button>
    <TerminalOutput :key="outputKey" :lines="outputLines.length ? outputLines : ['Output will appear here…']" :speed="8" />
  </div>
</template>
