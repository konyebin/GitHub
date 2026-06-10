(function () {
  "use strict";

  var panels = Array.from(document.querySelectorAll(".panel"));
  var railLinks = Array.from(document.querySelectorAll(".rail-link, .mobile-dot"));
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function setActiveNav(target) {
    railLinks.forEach(function (link) {
      link.classList.toggle("is-active", link.dataset.target === target);
    });
  }

  function getPanelIndex(target) {
    return panels.findIndex(function (panel) {
      return panel.dataset.panel === target;
    });
  }

  function scrollToPanel(index) {
    if (index < 0 || index >= panels.length) return;
    panels[index].scrollIntoView({
      behavior: reducedMotion ? "auto" : "smooth",
      block: "start",
    });
  }

  function initObserver() {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
            setActiveNav(entry.target.dataset.panel);
          }
        });
      },
      { threshold: [0.5, 0.75] }
    );

    panels.forEach(function (panel) {
      observer.observe(panel);
    });
  }

  document.addEventListener("keydown", function (event) {
    if (event.target && /input|textarea|select/i.test(event.target.tagName)) return;

    var active = document.querySelector(".rail-link.is-active, .mobile-dot.is-active");
    var currentTarget = active ? active.dataset.target : panels[0].dataset.panel;
    var index = getPanelIndex(currentTarget);

    if (event.key === "ArrowDown" || event.key === "PageDown") {
      event.preventDefault();
      scrollToPanel(index + 1);
    } else if (event.key === "ArrowUp" || event.key === "PageUp") {
      event.preventDefault();
      scrollToPanel(index - 1);
    } else if (event.key === "Home") {
      event.preventDefault();
      scrollToPanel(0);
    } else if (event.key === "End") {
      event.preventDefault();
      scrollToPanel(panels.length - 1);
    }
  });

  railLinks.forEach(function (link) {
    link.addEventListener("click", function (event) {
      var href = link.getAttribute("href");
      if (!href || !href.startsWith("#")) return;

      event.preventDefault();
      var target = document.querySelector(href);
      if (target) {
        target.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth" });
      }
    });
  });

  initObserver();
  if (panels[0]) setActiveNav(panels[0].dataset.panel);
})();
