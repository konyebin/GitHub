<script setup lang="ts">
import projectsData from "../data/projects.json";

function selectProject(projectId: string) {
  window.dispatchEvent(
    new CustomEvent("playground-select", { detail: { projectId } })
  );
  document.getElementById("playground")?.scrollIntoView({ behavior: "smooth" });
}
</script>

<template>
  <div class="scale-table-wrap routing-table">
    <table>
      <thead>
        <tr>
          <th>Task</th>
          <th>Project</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in projectsData.routing" :key="row.task">
          <td>{{ row.task }}</td>
          <td>
            <strong v-if="row.projectId">{{
              projectsData.projects.find((p) => p.id === row.projectId)?.name ?? row.projectId
            }}</strong>
            <strong v-else>root</strong>
          </td>
          <td>
            <button
              v-if="row.projectId"
              class="routing-try-btn"
              @click="selectProject(row.projectId)"
            >
              Try demo
            </button>
            <a v-else-if="row.link" :href="row.link">Setup</a>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
