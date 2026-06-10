(function () {
  "use strict";

  var panels = Array.from(document.querySelectorAll(".panel"));
  var railLinks = Array.from(document.querySelectorAll(".rail-link, .mobile-dot"));
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var ticking = false;

  function lerp(start, end, t) {
    return start + (end - start) * t;
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

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

  function updatePanelProgress() {
    var viewportHeight = window.innerHeight;
    var activeTarget = panels[0] ? panels[0].dataset.panel : "hero";

    panels.forEach(function (panel) {
      var inner = panel.querySelector(".panel-inner");
      if (!inner) return;

      var rect = panel.getBoundingClientRect();
      var panelHeight = panel.offsetHeight;
      var scrollable = panelHeight - viewportHeight;

      if (scrollable <= 0) {
        if (rect.top <= viewportHeight * 0.5 && rect.bottom >= viewportHeight * 0.5) {
          activeTarget = panel.dataset.panel;
        }
        if (!reducedMotion && !panel.classList.contains("panel--hero") && !panel.classList.contains("panel--close")) {
          inner.style.setProperty("--pull-offset", "0");
          inner.style.setProperty("--pull-opacity", "1");
        }
        return;
      }

      var scrolled = clamp(-rect.top, 0, scrollable);
      var progress = scrolled / scrollable;

      if (rect.top <= viewportHeight && rect.bottom >= 0) {
        activeTarget = panel.dataset.panel;
      }

      if (reducedMotion) {
        inner.style.setProperty("--pull-offset", "0");
        inner.style.setProperty("--pull-opacity", "1");
        return;
      }

      inner.style.setProperty("--pull-offset", lerp(12, 0, progress) + "vh");
      inner.style.setProperty("--pull-opacity", String(lerp(0.4, 1, progress)));
    });

    setActiveNav(activeTarget);
    ticking = false;
  }

  function onScroll() {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(updatePanelProgress);
    }
  }

  function initObserver() {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.35) {
            setActiveNav(entry.target.dataset.panel);
          }
        });
      },
      { threshold: [0.35, 0.55, 0.75] }
    );

    panels.forEach(function (panel) {
      observer.observe(panel);
    });
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });

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
  updatePanelProgress();
})();
