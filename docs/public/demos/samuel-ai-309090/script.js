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

  function updatePanelProgress() {
    var viewportHeight = window.innerHeight;
    var activeTarget = "hero";

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
        if (!reducedMotion && panel.dataset.panel !== "hero" && panel.dataset.panel !== "overview") {
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

      var offsetVh = lerp(12, 0, progress);
      var opacity = lerp(0.4, 1, progress);

      inner.style.setProperty("--pull-offset", offsetVh + "vh");
      inner.style.setProperty("--pull-opacity", String(opacity));
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
