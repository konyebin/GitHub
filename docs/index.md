---
layout: home
hero:
  name: Your projects deserve a clear map.
  text: One workspace. Every folder documented.
  tagline: Webex automation, MCP servers, scrapers, and experiments — try interactive demos before you run anything.
  actions:
    - theme: brand
      text: Try the playground
      link: /#playground
    - theme: alt
      text: Workspace setup
      link: /shared/root-setup
---

<div class="scale-ticker" aria-hidden="true">
  <div class="scale-ticker-track">
    <span>wxops</span><span>vidcastmcp</span><span>RoomOS</span><span>scrapeweb</span><span>Lookback</span><span>MCP</span><span>Check Back</span><span>CDR</span><span>wxcli</span><span>GenAI</span><span>wxops</span><span>vidcastmcp</span><span>RoomOS</span><span>scrapeweb</span><span>Lookback</span><span>MCP</span><span>Check Back</span><span>CDR</span><span>wxcli</span><span>GenAI</span>
  </div>
</div>

<div id="projects" class="scale-section">

<p class="scale-section-label">Playground</p>

## Try before you run.

<p style="color: var(--scale-text-muted); margin: -1rem 0 1.5rem; font-size: 0.95rem;">All 11 projects are in the left panel — use <strong>All projects</strong> to browse by name, or <strong>Find by task</strong> if you know what you want to do. Sample data only — no OAuth or API calls.</p>

<ClientOnly>
  <ProjectPlayground />
</ClientOnly>

</div>

<div class="scale-cta">

### Run the docs locally

<p>From your machine — same commands, better presentation.</p>

```bash
cd ~/Documents/GitHub/docs
npm install
npm run docs:dev
```

</div>

<div class="scale-section">

<p class="scale-section-label">Canonical sources</p>

## Trust the repo first

Agent and setup instructions live in **`CLAUDE.md`** at the repo root and in each project. This site summarizes those files; when they diverge, trust the **`CLAUDE.md`** in the repo.

</div>
