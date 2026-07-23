(function () {
  "use strict";

  // ---- Theme toggle (default: system preference, override persisted in localStorage) ----
  var root = document.documentElement;
  var stored = localStorage.getItem("nexus-theme");
  if (stored) root.setAttribute("data-theme", stored);

  function currentTheme() {
    var attr = root.getAttribute("data-theme");
    if (attr) return attr;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyThemeButton() {
    var btn = document.getElementById("theme-toggle");
    if (btn) btn.textContent = currentTheme() === "dark" ? "☀" : "☽";
  }

  document.addEventListener("DOMContentLoaded", function () {
    applyThemeButton();
    var btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.addEventListener("click", function () {
        var next = currentTheme() === "dark" ? "light" : "dark";
        root.setAttribute("data-theme", next);
        localStorage.setItem("nexus-theme", next);
        applyThemeButton();
      });
    }

    // ---- Copy-to-clipboard for result blocks ----
    document.querySelectorAll("[data-copy-target]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var target = document.getElementById(btn.getAttribute("data-copy-target"));
        if (!target) return;
        var text = target.textContent;
        navigator.clipboard.writeText(text).then(function () {
          var original = btn.textContent;
          btn.textContent = "Copied!";
          setTimeout(function () { btn.textContent = original; }, 1200);
        }).catch(function () {
          btn.textContent = "Copy failed";
        });
      });
    });

    // ---- Drag-and-drop styling for file upload zones ----
    document.querySelectorAll(".dropzone").forEach(function (zone) {
      var input = zone.querySelector("input[type=file]");
      if (!input) return;

      var label = zone.querySelector(".dropzone-label");

      function setFilename() {
        if (input.files && input.files.length > 0 && label) {
          label.textContent = input.files[0].name;
        }
      }
      input.addEventListener("change", setFilename);

      ["dragenter", "dragover"].forEach(function (evt) {
        zone.addEventListener(evt, function (e) {
          e.preventDefault();
          e.stopPropagation();
          zone.classList.add("dragover");
        });
      });
      ["dragleave", "drop"].forEach(function (evt) {
        zone.addEventListener(evt, function (e) {
          e.preventDefault();
          e.stopPropagation();
          zone.classList.remove("dragover");
        });
      });
      zone.addEventListener("drop", function (e) {
        var files = e.dataTransfer.files;
        if (files && files.length > 0) {
          input.files = files;
          setFilename();
        }
      });
    });

    // ---- Loading state on form submit ----
    document.querySelectorAll("form").forEach(function (form) {
      form.addEventListener("submit", function () {
        var btn = form.querySelector("button[type=submit]");
        if (btn && !btn.disabled) {
          btn.dataset.originalText = btn.textContent;
          btn.textContent = "Working...";
          btn.disabled = true;
        }
      });
    });
  });
})();
