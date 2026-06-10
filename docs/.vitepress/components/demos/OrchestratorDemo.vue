<script setup lang="ts">
import { ref } from "vue";
import servers from "../../data/demo-samples/mcp-servers.json";

const expanded = ref<string | null>(null);

function toggle(name: string) {
  expanded.value = expanded.value === name ? null : name;
}
</script>

<template>
  <div class="demo-orchestrator">
    <div class="demo-mini-title">Registered MCP Servers</div>
    <div class="demo-mcp-grid">
      <div
        v-for="srv in servers"
        :key="srv.name"
        class="demo-mcp-card"
        :class="{ expanded: expanded === srv.name }"
        @click="toggle(srv.name)"
      >
        <div class="demo-mcp-header">
          <span class="demo-mcp-name">{{ srv.name }}</span>
          <span class="demo-mcp-transport">{{ srv.transport }}</span>
        </div>
        <p class="demo-mcp-desc">{{ srv.description }}</p>
        <div class="demo-mcp-tools">{{ srv.tools }} tools</div>
        <Transition name="slide-in">
          <div v-if="expanded === srv.name" class="demo-mcp-readme">
            <code>{{ srv.readme }}</code>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>
