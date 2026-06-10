<script setup lang="ts">
import { ref, computed } from "vue";

type CallState = "idle" | "dialing" | "connected" | "held";

const deviceName = "Boardroom SX80";
const callState = ref<CallState>("idle");
const muted = ref(false);
const cameraPreset = ref<number | null>(null);
const dialed = ref("");
const log = ref<string[]>([]);

const statusText = computed(() => {
  if (callState.value === "idle") return "Ready";
  if (callState.value === "dialing") return "Dialing…";
  if (callState.value === "held") return "On Hold";
  return muted.value ? "Connected (Muted)" : "Connected";
});

function addLog(msg: string) {
  log.value = [`[${new Date().toLocaleTimeString()}] ${msg}`, ...log.value].slice(0, 6);
}

function pressDigit(d: string) {
  dialed.value += d;
}

function dial() {
  if (!dialed.value) return;
  callState.value = "dialing";
  addLog(`xAPI: Dial ${dialed.value}`);
  setTimeout(() => {
    callState.value = "connected";
    addLog("Call connected");
  }, 1200);
}

function hangup() {
  callState.value = "idle";
  muted.value = false;
  dialed.value = "";
  addLog("Call ended");
}

function toggleMute() {
  if (callState.value !== "connected" && callState.value !== "held") return;
  muted.value = !muted.value;
  addLog(muted.value ? "Audio muted" : "Audio unmuted");
}

function toggleHold() {
  if (callState.value === "connected") {
    callState.value = "held";
    addLog("Call on hold");
  } else if (callState.value === "held") {
    callState.value = "connected";
    addLog("Call resumed");
  }
}

function setPreset(n: number) {
  cameraPreset.value = n;
  addLog(`Camera preset ${n} activated`);
}

function standby() {
  hangup();
  addLog("Standby mode activated");
}
</script>

<template>
  <div class="demo-device">
    <div class="demo-device-header">
      <span class="demo-device-icon">📹</span>
      <div>
        <div class="demo-device-name">{{ deviceName }}</div>
        <div class="demo-device-status" :class="callState">{{ statusText }}</div>
      </div>
    </div>

    <div class="demo-dial-display">{{ dialed || "Enter number…" }}</div>

    <div class="demo-dialpad">
      <button v-for="d in ['1','2','3','4','5','6','7','8','9','*','0','#']" :key="d" @click="pressDigit(d)">{{ d }}</button>
    </div>

    <div class="demo-device-controls">
      <button class="demo-ctrl green" :disabled="!dialed || callState !== 'idle'" @click="dial">Dial</button>
      <button class="demo-ctrl red" :disabled="callState === 'idle'" @click="hangup">Hang Up</button>
      <button class="demo-ctrl" :disabled="callState === 'idle'" @click="toggleMute">{{ muted ? "Unmute" : "Mute" }}</button>
      <button class="demo-ctrl" :disabled="callState === 'idle' || callState === 'dialing'" @click="toggleHold">
        {{ callState === "held" ? "Resume" : "Hold" }}
      </button>
    </div>

    <div class="demo-presets">
      <span class="demo-mini-title">Camera Presets</span>
      <button
        v-for="n in 4"
        :key="n"
        class="demo-preset-btn"
        :class="{ active: cameraPreset === n }"
        @click="setPreset(n)"
      >
        {{ n }}
      </button>
      <button class="demo-ctrl outline" @click="standby">Standby</button>
    </div>

    <div class="demo-device-log">
      <div v-for="(entry, i) in log" :key="i" class="demo-log-line">{{ entry }}</div>
      <div v-if="!log.length" class="demo-log-empty">xAPI command log appears here</div>
    </div>
  </div>
</template>
