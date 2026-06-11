<script setup lang="ts">
import { ref, computed } from "vue";
import sample from "../../data/demo-samples/checkback-sample.json";

const healthFilter = ref<string>("all");
const selectedAccount = ref(sample.accounts[0].name);

const filteredAccounts = computed(() => {
  if (healthFilter.value === "all") return sample.accounts;
  return sample.accounts.filter((a) => a.health === healthFilter.value);
});

function healthColor(h: string) {
  return h === "green" ? "#00d4a0" : h === "yellow" ? "#fbbf24" : "#ff6b35";
}

function kpiColor(status: string) {
  return healthColor(status);
}
</script>

<template>
  <div class="demo-checkback">
    <div class="demo-checkback-header">
      <span class="demo-checkback-account">{{ sample.account }}</span>
      <span class="demo-checkback-renewal">Renewal: {{ sample.renewalDate }}</span>
    </div>

    <div class="demo-kpi-grid">
      <div v-for="kpi in sample.kpis" :key="kpi.label" class="demo-kpi-card">
        <span class="demo-kpi-label">{{ kpi.label }}</span>
        <span class="demo-kpi-value" :style="{ color: kpiColor(kpi.status) }">{{ kpi.value }}</span>
      </div>
    </div>

    <div class="demo-checkback-filters">
      <label>
        Health
        <select v-model="healthFilter" class="demo-select">
          <option value="all">All</option>
          <option value="green">Green</option>
          <option value="yellow">Yellow</option>
          <option value="red">Red</option>
        </select>
      </label>
      <label>
        Account
        <select v-model="selectedAccount" class="demo-select">
          <option v-for="a in sample.accounts" :key="a.name" :value="a.name">{{ a.name }}</option>
        </select>
      </label>
    </div>

    <div class="demo-license-bars">
      <div v-for="lic in sample.licenses" :key="lic.name" class="demo-license-row">
        <span class="demo-license-name">{{ lic.name }}</span>
        <div class="demo-license-track">
          <div
            class="demo-license-active"
            :style="{ width: (lic.active / lic.purchased) * 100 + '%' }"
          />
          <div
            class="demo-license-assigned"
            :style="{ width: (lic.assigned / lic.purchased) * 100 + '%' }"
          />
        </div>
        <span class="demo-license-stats">{{ lic.active }}/{{ lic.purchased }}</span>
      </div>
    </div>

    <div class="demo-account-grid">
      <div
        v-for="acc in filteredAccounts"
        :key="acc.name"
        class="demo-account-card"
        :class="{ selected: acc.name === selectedAccount }"
        @click="selectedAccount = acc.name"
      >
        <span class="demo-account-dot" :style="{ background: healthColor(acc.health) }" />
        <span class="demo-account-name">{{ acc.name }}</span>
        <span class="demo-account-util">{{ acc.utilization }}%</span>
      </div>
    </div>
  </div>
</template>
