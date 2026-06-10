<script setup lang="ts">
import { computed, defineAsyncComponent } from "vue";
import projectsData from "../data/projects.json";
import DemoFrame from "./DemoFrame.vue";

const props = defineProps<{
  slug: string;
  compact?: boolean;
}>();

const demoComponents: Record<string, ReturnType<typeof defineAsyncComponent>> = {
  WxopsDemo: defineAsyncComponent(() => import("./demos/WxopsDemo.vue")),
  VidcastmcpDemo: defineAsyncComponent(() => import("./demos/VidcastmcpDemo.vue")),
  DeviceMcpDemo: defineAsyncComponent(() => import("./demos/DeviceMcpDemo.vue")),
  ScrapewebDemo: defineAsyncComponent(() => import("./demos/ScrapewebDemo.vue")),
  LookbackDemo: defineAsyncComponent(() => import("./demos/LookbackDemo.vue")),
  OrchestratorDemo: defineAsyncComponent(() => import("./demos/OrchestratorDemo.vue")),
  CheckBackDemo: defineAsyncComponent(() => import("./demos/CheckBackDemo.vue")),
  TestDemo: defineAsyncComponent(() => import("./demos/TestDemo.vue")),
  GenaiDemo: defineAsyncComponent(() => import("./demos/GenaiDemo.vue")),
  DroneDemo: defineAsyncComponent(() => import("./demos/DroneDemo.vue")),
};

const project = computed(() =>
  projectsData.projects.find((p) => p.id === props.slug)
);

const demoComponent = computed(() => {
  const comp = project.value?.demo?.component;
  return comp ? demoComponents[comp] : null;
});

const isIframe = computed(() => project.value?.demo?.type === "iframe");
</script>

<template>
  <div v-if="project" class="demo-panel" :class="{ 'demo-panel--compact': compact }">
    <div v-if="!compact" class="demo-panel-header">
      <span class="demo-panel-badge">Try it</span>
      <span class="demo-panel-label">Interactive preview — sample data only</span>
    </div>
    <ClientOnly>
      <DemoFrame
        v-if="isIframe && project.demo?.src"
        :src="project.demo.src"
        :height="project.demo.height"
        :title="project.name"
      />
      <component :is="demoComponent" v-else-if="demoComponent" />
      <div v-else class="demo-panel-fallback">No demo available for this project.</div>
    </ClientOnly>
  </div>
</template>
