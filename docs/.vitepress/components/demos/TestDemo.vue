<script setup lang="ts">
import { ref } from "vue";

const messages = ref([
  { from: "bot", text: "Send me a Control Hub screenshot and I'll extract the metrics." },
]);

const ocrFields = ref<{ label: string; value: string }[]>([]);
const processing = ref(false);

const sampleFields = [
  { label: "Registered Devices", value: "1,247" },
  { label: "Active Users", value: "891" },
  { label: "Meeting Minutes", value: "42,180" },
  { label: "Quality Score", value: "4.2" },
];

function simulateUpload() {
  if (processing.value) return;
  messages.value.push({ from: "user", text: "📎 dashboard_screenshot.png" });
  processing.value = true;
  messages.value.push({ from: "bot", text: "Processing screenshot with OCR…" });

  setTimeout(() => {
    ocrFields.value = sampleFields;
    processing.value = false;
    messages.value.push({
      from: "bot",
      text: "✓ Extracted 4 metrics. Appended row to CheckBack.xlsx",
    });
  }, 1800);
}
</script>

<template>
  <div class="demo-test">
    <div class="demo-webex-thread">
      <div class="demo-thread-header">Webex Space — #check-back-bot</div>
      <div class="demo-messages">
        <div
          v-for="(msg, i) in messages"
          :key="i"
          class="demo-message"
          :class="msg.from"
        >
          {{ msg.text }}
        </div>
      </div>
      <button class="demo-btn primary" :disabled="processing" @click="simulateUpload">
        {{ processing ? "Processing…" : "Send Sample Screenshot" }}
      </button>
    </div>
    <div class="demo-ocr-result">
      <div class="demo-mini-title">Extracted Fields → Excel Row</div>
      <table v-if="ocrFields.length" class="demo-excel-table">
        <thead>
          <tr><th>Field</th><th>Value</th></tr>
        </thead>
        <tbody>
          <tr v-for="f in ocrFields" :key="f.label">
            <td>{{ f.label }}</td>
            <td>{{ f.value }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="demo-json-empty">OCR results appear after upload</p>
    </div>
  </div>
</template>
