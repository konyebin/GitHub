<script setup lang="ts">
import { ref, computed } from "vue";

interface PageNode {
  id: string;
  url: string;
  title: string;
  depth: number;
  links: number;
  headings: string[];
  children?: PageNode[];
}

const siteTree: PageNode[] = [
  {
    id: "root",
    url: "https://example.com",
    title: "Home",
    depth: 0,
    links: 3,
    headings: ["Welcome", "Products", "Contact"],
    children: [
      {
        id: "products",
        url: "https://example.com/products",
        title: "Products",
        depth: 1,
        links: 2,
        headings: ["All Products", "Pricing"],
        children: [
          {
            id: "prod-a",
            url: "https://example.com/products/a",
            title: "Product A",
            depth: 2,
            links: 0,
            headings: ["Features", "Specs"],
          },
          {
            id: "prod-b",
            url: "https://example.com/products/b",
            title: "Product B",
            depth: 2,
            links: 0,
            headings: ["Overview", "Reviews"],
          },
        ],
      },
      {
        id: "about",
        url: "https://example.com/about",
        title: "About",
        depth: 1,
        links: 1,
        headings: ["Our Story", "Team"],
        children: [
          {
            id: "team",
            url: "https://example.com/about/team",
            title: "Team",
            depth: 2,
            links: 0,
            headings: ["Leadership", "Careers"],
          },
        ],
      },
      {
        id: "contact",
        url: "https://example.com/contact",
        title: "Contact",
        depth: 1,
        links: 0,
        headings: ["Get in Touch", "Office Locations"],
      },
    ],
  },
];

const discovered = ref<string[]>([]);
const crawling = ref(false);
const selectedNode = ref<PageNode | null>(null);
const crawlDone = ref(false);

const flatOrder = ["root", "products", "prod-a", "prod-b", "about", "team", "contact"];

function findNode(id: string, nodes: PageNode[] = siteTree): PageNode | null {
  for (const n of nodes) {
    if (n.id === id) return n;
    if (n.children) {
      const found = findNode(id, n.children);
      if (found) return found;
    }
  }
  return null;
}

const visibleNodes = computed(() => flatOrder.filter((id) => discovered.value.includes(id)));

function startCrawl() {
  if (crawling.value) return;
  discovered.value = [];
  selectedNode.value = null;
  crawlDone.value = false;
  crawling.value = true;
  let i = 0;
  const interval = setInterval(() => {
    if (i < flatOrder.length) {
      discovered.value.push(flatOrder[i]);
      i++;
    } else {
      clearInterval(interval);
      crawling.value = false;
      crawlDone.value = true;
    }
  }, 500);
}

function selectNode(id: string) {
  selectedNode.value = findNode(id);
}

const jsonPreview = computed(() => {
  if (!selectedNode.value) return null;
  const n = selectedNode.value;
  return JSON.stringify(
    {
      url: n.url,
      title: n.title,
      depth: n.depth,
      links_found: n.links,
      headings: n.headings,
    },
    null,
    2
  );
});
</script>

<template>
  <div class="demo-scrapeweb">
    <div class="demo-scrapeweb-toolbar">
      <span class="demo-scrapeweb-url">https://example.com</span>
      <button class="demo-btn primary" :disabled="crawling" @click="startCrawl">
        {{ crawling ? "Crawling…" : crawlDone ? "Re-crawl" : "Start BFS Crawl" }}
      </button>
      <span v-if="crawlDone" class="demo-scrapeweb-stat">{{ discovered.length }} pages</span>
    </div>
    <div class="demo-scrapeweb-body">
      <div class="demo-tree">
        <div class="demo-mini-title">Site Map (BFS order)</div>
        <div
          v-for="id in visibleNodes"
          :key="id"
          class="demo-tree-node"
          :class="{ active: selectedNode?.id === id, [`depth-${findNode(id)?.depth}`]: true }"
          @click="selectNode(id)"
        >
          <span class="demo-tree-dot" />
          {{ findNode(id)?.title }}
          <span class="demo-tree-url">{{ findNode(id)?.url.replace("https://example.com", "") || "/" }}</span>
        </div>
        <div v-if="!visibleNodes.length" class="demo-tree-empty">Click Start to crawl</div>
      </div>
      <div class="demo-json-panel">
        <div class="demo-mini-title">Page JSON</div>
        <pre v-if="jsonPreview" class="demo-json">{{ jsonPreview }}</pre>
        <p v-else class="demo-json-empty">Click a node to see extracted data</p>
      </div>
    </div>
  </div>
</template>
