<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import projectsData from "../data/projects.json";
import DemoPanel from "./DemoPanel.vue";

const props = defineProps<{
  initialProject?: string;
}>();

const search = ref("");
const activeCategory = ref<string | null>(null);
const railView = ref<"projects" | "tasks">("projects");
const selectedId = ref(props.initialProject ?? projectsData.projects[0]?.id ?? "");
const copied = ref(false);

const categories = projectsData.categories;

const filteredProjects = computed(() => {
  let list = projectsData.projects;
  if (activeCategory.value) {
    list = list.filter((p) => p.categories.includes(activeCategory.value!));
  }
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    list = list.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.tagline.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q)
    );
  }
  return list;
});

const selected = computed(() =>
  projectsData.projects.find((p) => p.id === selectedId.value)
);

const selectedIndex = computed(() =>
  filteredProjects.value.findIndex((p) => p.id === selectedId.value)
);

function selectProject(id: string) {
  selectedId.value = id;
  railView.value = "projects";
  const el = document.getElementById("playground");
  el?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function selectByTask(projectId: string) {
  selectProject(projectId);
}

function selectByIndex(delta: number) {
  const list = filteredProjects.value;
  if (!list.length) return;
  let idx = selectedIndex.value;
  if (idx < 0) idx = 0;
  idx = (idx + delta + list.length) % list.length;
  selectedId.value = list[idx].id;
}

function onKeydown(e: KeyboardEvent) {
  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
  if (e.key === "ArrowDown") {
    e.preventDefault();
    selectByIndex(1);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    selectByIndex(-1);
  }
}

async function copyCommand() {
  if (!selected.value?.runCommand) return;
  try {
    await navigator.clipboard.writeText(selected.value.runCommand);
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  } catch {
    /* clipboard unavailable */
  }
}

function categoryColor(id: string) {
  return categories.find((c) => c.id === id)?.color ?? "#94a3b8";
}

watch(filteredProjects, (list) => {
  if (list.length && !list.some((p) => p.id === selectedId.value)) {
    selectedId.value = list[0].id;
  }
});

onMounted(() => {
  window.addEventListener("keydown", onKeydown);
  window.addEventListener("playground-select", ((e: CustomEvent) => {
    if (e.detail?.projectId) selectProject(e.detail.projectId);
  }) as EventListener);
});

onUnmounted(() => {
  window.removeEventListener("keydown", onKeydown);
});

defineExpose({ selectProject });
</script>

<template>
  <div id="playground" class="playground">
    <aside class="playground-rail">
      <div class="playground-rail-tabs">
        <button
          class="playground-rail-tab"
          :class="{ active: railView === 'projects' }"
          @click="railView = 'projects'"
        >
          All projects
          <span class="playground-rail-count">{{ filteredProjects.length }}</span>
        </button>
        <button
          class="playground-rail-tab"
          :class="{ active: railView === 'tasks' }"
          @click="railView = 'tasks'"
        >
          Find by task
        </button>
      </div>

      <div v-if="railView === 'projects'" class="playground-rail-body">
        <div class="playground-search-wrap">
          <input
            v-model="search"
            type="search"
            class="playground-search"
            placeholder="Search projects…"
            aria-label="Search projects"
          />
        </div>
        <div class="playground-filters">
          <button
            class="playground-filter"
            :class="{ active: !activeCategory }"
            @click="activeCategory = null"
          >
            All
          </button>
          <button
            v-for="cat in categories"
            :key="cat.id"
            class="playground-filter"
            :class="{ active: activeCategory === cat.id }"
            :style="{ '--cat-color': cat.color }"
            @click="activeCategory = activeCategory === cat.id ? null : cat.id"
          >
            {{ cat.label }}
          </button>
        </div>
        <ul class="playground-list" role="listbox" aria-label="Projects">
          <li
            v-for="project in filteredProjects"
            :key="project.id"
            role="option"
            :aria-selected="project.id === selectedId"
            class="playground-item"
            :class="{ active: project.id === selectedId }"
            @click="selectProject(project.id)"
          >
            <span class="playground-item-name">{{ project.name }}</span>
            <span class="playground-item-badges">
              <span
                v-for="cat in project.categories.slice(0, 2)"
                :key="cat"
                class="playground-cat-dot"
                :style="{ background: categoryColor(cat) }"
                :title="categories.find((c) => c.id === cat)?.label"
              />
            </span>
          </li>
        </ul>
        <p class="playground-hint">↑↓ to navigate · scroll for all {{ filteredProjects.length }} projects</p>
      </div>

      <div v-else class="playground-rail-body">
        <p class="playground-task-intro">Pick a task — the matching project demo loads on the right.</p>
        <ul class="playground-task-list">
          <li
            v-for="row in projectsData.routing"
            :key="row.task"
            class="playground-task-item"
            :class="{ active: row.projectId === selectedId }"
            @click="row.projectId && selectByTask(row.projectId)"
          >
            <span class="playground-task-text">{{ row.task }}</span>
            <span v-if="row.projectId" class="playground-task-project">
              → {{ projectsData.projects.find((p) => p.id === row.projectId)?.name }}
            </span>
            <a v-else-if="row.link" :href="row.link" class="playground-task-link">Setup →</a>
          </li>
        </ul>
      </div>
    </aside>

    <main class="playground-main">
      <Transition name="demo-fade" mode="out-in">
        <div v-if="selected" :key="selected.id" class="playground-demo-wrap">
          <DemoPanel :slug="selected.id" compact />
        </div>
      </Transition>
    </main>

    <aside class="playground-info">
      <Transition name="demo-fade" mode="out-in">
        <div v-if="selected" :key="selected.id" class="playground-info-inner">
          <h3 class="playground-info-title">{{ selected.name }}</h3>
          <p class="playground-info-desc">{{ selected.description }}</p>
          <div class="playground-info-cats">
            <span
              v-for="cat in selected.categories"
              :key="cat"
              class="playground-info-cat"
              :style="{ borderColor: categoryColor(cat), color: categoryColor(cat) }"
            >
              {{ categories.find((c) => c.id === cat)?.label }}
            </span>
          </div>
          <div class="playground-run">
            <label class="playground-run-label">Run for real</label>
            <code class="playground-run-cmd">{{ selected.runCommand }}</code>
            <button class="playground-copy-btn" @click="copyCommand">
              {{ copied ? "Copied!" : "Copy" }}
            </button>
          </div>
          <a :href="selected.path" class="playground-docs-link">Full documentation →</a>
        </div>
      </Transition>
    </aside>
  </div>
</template>
