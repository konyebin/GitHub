<script setup lang="ts">
import { ref, computed } from "vue";
import TerminalOutput from "../TerminalOutput.vue";

const commands = [
  {
    cmd: "wxcli whoami",
    output: [
      "wxcli whoami",
      "Organization: Acme Corp (Y2lzY29zcGFy...) ",
      "User: admin@acme.com",
      "Roles: Full Administrator",
    ],
  },
  {
    cmd: "wxcli telephony v2 locations list",
    output: [
      "wxcli telephony v2 locations list",
      "ID                    NAME              STATUS",
      "Y2lz...abc123          HQ - New York     active",
      "Y2lz...def456          Branch - Austin     active",
      "Y2lz...ghi789          Remote - London     active",
      "3 locations found.",
    ],
  },
  {
    cmd: "wxcli reports cdr list --hours 12",
    output: [
      "wxcli reports cdr list --hours 12",
      "Fetching CDR from analytics-calling.webexapis.com...",
      "Window: 2026-05-28T00:00Z → 2026-05-28T12:00Z",
      "Records: 847",
      "Saved to: ./reports/cdr_20260528.csv",
    ],
  },
];

const selectedCmd = ref(commands[0].cmd);
const outputKey = ref(0);

const currentOutput = computed(
  () => commands.find((c) => c.cmd === selectedCmd.value)?.output ?? []
);

function runCommand(cmd: string) {
  selectedCmd.value = cmd;
  outputKey.value++;
}

const cdrRows = [
  { time: "09:14:22", from: "+1 512-555-0100", to: "+1 512-555-0199", dur: "4:32", dir: "Outbound" },
  { time: "09:18:05", from: "+1 212-555-0142", to: "Queue: Support", dur: "2:15", dir: "Inbound" },
  { time: "09:22:41", from: "+1 415-555-0188", to: "+1 415-555-0177", dur: "8:01", dir: "Outbound" },
  { time: "09:31:09", from: "AA: Main Menu", to: "+1 512-555-0100", dur: "0:45", dir: "Internal" },
];

const billingBars = [
  { label: "Calling", pct: 72 },
  { label: "Meetings", pct: 89 },
  { label: "Contact Center", pct: 48 },
  { label: "Devices", pct: 91 },
];
</script>

<template>
  <div class="demo-wxops">
    <div class="demo-wxops-cmd-row">
      <button
        v-for="c in commands"
        :key="c.cmd"
        class="demo-chip"
        :class="{ active: selectedCmd === c.cmd }"
        @click="runCommand(c.cmd)"
      >
        {{ c.cmd }}
      </button>
    </div>
    <TerminalOutput :key="outputKey" :lines="currentOutput" />
    <div class="demo-wxops-grid">
      <div class="demo-mini-table">
        <div class="demo-mini-title">CDR Preview</div>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>From</th>
              <th>To</th>
              <th>Dur</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in cdrRows" :key="i">
              <td>{{ row.time }}</td>
              <td>{{ row.from }}</td>
              <td>{{ row.to }}</td>
              <td>{{ row.dur }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="demo-billing-chart">
        <div class="demo-mini-title">License Usage</div>
        <div v-for="bar in billingBars" :key="bar.label" class="demo-bar-row">
          <span class="demo-bar-label">{{ bar.label }}</span>
          <div class="demo-bar-track">
            <div class="demo-bar-fill" :style="{ width: bar.pct + '%' }" />
          </div>
          <span class="demo-bar-pct">{{ bar.pct }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>
