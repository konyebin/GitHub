<script setup lang="ts">
import { ref, computed } from "vue";
import recordings from "../../data/demo-samples/recordings.json";

const query = ref("");
const selected = ref<typeof recordings[0] | null>(null);

const filtered = computed(() => {
  const q = query.value.toLowerCase();
  if (!q) return recordings;
  return recordings.filter(
    (r) =>
      r.title.toLowerCase().includes(q) ||
      r.presenter.toLowerCase().includes(q) ||
      r.transcript.toLowerCase().includes(q)
  );
});

function selectRec(rec: typeof recordings[0]) {
  selected.value = selected.value?.id === rec.id ? null : rec;
}
</script>

<template>
  <div class="demo-vidcast">
    <input
      v-model="query"
      type="search"
      class="demo-search"
      placeholder="Search recordings, presenters, transcripts…"
    />
    <div class="demo-vidcast-layout">
      <ul class="demo-rec-list">
        <li
          v-for="rec in filtered"
          :key="rec.id"
          class="demo-rec-item"
          :class="{ active: selected?.id === rec.id }"
          @click="selectRec(rec)"
        >
          <span class="demo-rec-title">{{ rec.title }}</span>
          <span class="demo-rec-meta">{{ rec.presenter }} · {{ rec.duration }} · {{ rec.date }}</span>
        </li>
      </ul>
      <Transition name="slide-in">
        <div v-if="selected" class="demo-transcript-panel">
          <h4>{{ selected.title }}</h4>
          <p class="demo-transcript-text">{{ selected.transcript }}</p>
        </div>
        <div v-else class="demo-transcript-placeholder">
          Select a recording to view transcript
        </div>
      </Transition>
    </div>
  </div>
</template>
