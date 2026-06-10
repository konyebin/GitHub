<script setup lang="ts">
import { ref } from "vue";

const metrics = [
  { label: "Registered Devices", value: "1,247", confidence: "HIGH" },
  { label: "Active Users (30d)", value: "891", confidence: "HIGH" },
  { label: "Meeting Minutes", value: "42,180", confidence: "MEDIUM" },
  { label: "Call Quality Score", value: "4.2 / 5", confidence: "MEDIUM" },
  { label: "Unused Licenses", value: "156", confidence: "LOW" },
  { label: "Avg Call Duration", value: "6:42", confidence: "HIGH" },
];

const ocrRunning = ref(false);
const ocrDone = ref(false);

function runOcr() {
  ocrRunning.value = true;
  ocrDone.value = false;
  setTimeout(() => {
    ocrRunning.value = false;
    ocrDone.value = true;
  }, 1500);
}

function confidenceClass(c: string) {
  return c.toLowerCase();
}
</script>

<template>
  <div class="demo-lookback">
    <div class="demo-lookback-split">
      <div class="demo-screenshot-panel">
        <div class="demo-mini-title">Control Hub Screenshot</div>
        <div class="demo-fake-dashboard">
          <div class="demo-fake-header">Webex Control Hub</div>
          <div class="demo-fake-cards">
            <div class="demo-fake-card"><span>Devices</span><strong>1,247</strong></div>
            <div class="demo-fake-card"><span>Users</span><strong>891</strong></div>
            <div class="demo-fake-card"><span>Minutes</span><strong>42.1K</strong></div>
            <div class="demo-fake-card"><span>Quality</span><strong>4.2</strong></div>
          </div>
          <div class="demo-fake-chart" />
        </div>
        <button class="demo-btn primary" :disabled="ocrRunning" @click="runOcr">
          {{ ocrRunning ? "Running OCR…" : "Extract Metrics" }}
        </button>
      </div>
      <div class="demo-excel-panel">
        <div class="demo-mini-title">Excel Output</div>
        <table class="demo-excel-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Value</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(m, i) in metrics" :key="m.label" :class="{ 'row-reveal': ocrDone, [`delay-${i}`]: true }">
              <td>{{ m.label }}</td>
              <td>{{ ocrDone ? m.value : "—" }}</td>
              <td>
                <span v-if="ocrDone" class="demo-confidence" :class="confidenceClass(m.confidence)">
                  {{ m.confidence }}
                </span>
                <span v-else>—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.row-reveal {
  animation: rowReveal 0.4s ease forwards;
  opacity: 0;
}
.delay-0 { animation-delay: 0.1s; }
.delay-1 { animation-delay: 0.2s; }
.delay-2 { animation-delay: 0.3s; }
.delay-3 { animation-delay: 0.4s; }
.delay-4 { animation-delay: 0.5s; }
.delay-5 { animation-delay: 0.6s; }
@keyframes rowReveal {
  to { opacity: 1; }
}
</style>
