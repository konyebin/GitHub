import DefaultTheme from "vitepress/theme";
import "./custom.css";
import ProjectPlayground from "../components/ProjectPlayground.vue";
import DemoPanel from "../components/DemoPanel.vue";
import DemoFrame from "../components/DemoFrame.vue";
import TerminalOutput from "../components/TerminalOutput.vue";
import RoutingTable from "../components/RoutingTable.vue";

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component("ProjectPlayground", ProjectPlayground);
    app.component("DemoPanel", DemoPanel);
    app.component("DemoFrame", DemoFrame);
    app.component("TerminalOutput", TerminalOutput);
    app.component("RoutingTable", RoutingTable);
  },
};
