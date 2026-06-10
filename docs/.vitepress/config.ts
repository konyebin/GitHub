import { defineConfig } from "vitepress";

export default defineConfig({
  title: "GitHub Workspace",
  description: "Documentation hub for ~/Documents/GitHub projects",
  lang: "en-US",
  base: "/GitHub/",
  appearance: "dark",
  head: [
    ["link", { rel: "preconnect", href: "https://fonts.googleapis.com" }],
    ["link", { rel: "preconnect", href: "https://fonts.gstatic.com", crossorigin: "" }],
    [
      "link",
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap",
      },
    ],
  ],
  themeConfig: {
    logo: {
      light: undefined,
      dark: undefined,
      alt: "GitHub Workspace",
    },
    siteTitle: "GitHub Workspace",
    nav: [
      { text: "Playground", link: "/#playground" },
      { text: "Setup", link: "/shared/root-setup" },
    ],
    sidebar: [
      {
        text: "Workspace",
        items: [
          { text: "Overview", link: "/" },
          { text: "Root setup (OAuth, MCP)", link: "/shared/root-setup" },
        ],
      },
      {
        text: "Projects",
        items: [
          { text: "wxops", link: "/projects/wxops" },
          { text: "vidcastmcp", link: "/projects/vidcastmcp" },
          { text: "scrapeweb", link: "/projects/scrapeweb" },
          { text: "Lookback", link: "/projects/lookback" },
          { text: "my-orchestrator", link: "/projects/my-orchestrator" },
          { text: "check-back-intelligence", link: "/projects/check-back-intelligence" },
          { text: "test", link: "/projects/test" },
          { text: "device-mcp-server", link: "/projects/device-mcp-server" },
          { text: "GenAI-Bootcamp", link: "/projects/genai-bootcamp" },
          { text: "AI Receptionist deck", link: "/projects/ai-receptionist-deck" },
          { text: "CTFMonopoly", link: "/projects/ctfmonopoly" },
          { text: "Autonomous-Ai-drone-scripts", link: "/projects/autonomous-ai-drone-scripts" },
        ],
      },
    ],
    search: {
      provider: "local",
    },
    socialLinks: [],
    footer: {
      message: "Canonical context lives in each project’s CLAUDE.md",
      copyright: "Personal workspace · ~/Documents/GitHub",
    },
    docFooter: {
      prev: "Previous",
      next: "Next",
    },
    outline: {
      level: [2, 3],
      label: "On this page",
    },
  },
});
