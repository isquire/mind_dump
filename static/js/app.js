/* =========================================================
   Mind Dump — App JavaScript
   Handles: delete confirmations, auto-focus quick capture,
   Bootstrap tooltip init.
   ========================================================= */

'use strict';

document.addEventListener('DOMContentLoaded', function () {

  // ── Delete confirmation ─────────────────────────────────
  // Any form with data-confirm attribute will prompt before submit
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      var msg = this.dataset.confirm || 'Are you sure?';
      if (!window.confirm(msg)) {
        e.preventDefault();
      }
    });
  });

  // ── Auto-focus quick capture on Dashboard ──────────────
  var captureInput = document.getElementById('quick-capture-input');
  if (captureInput) {
    // Only auto-focus if nothing else is focused and no hash in URL
    if (!window.location.hash && document.activeElement === document.body) {
      captureInput.focus();
    }
  }

  // ── Bootstrap tooltips ─────────────────────────────────
  var tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipEls.forEach(function (el) {
    new bootstrap.Tooltip(el);
  });

  // ── Night mode toggle ───────────────────────────────────
  var themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    function updateThemeIcon() {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      themeToggle.querySelector('i').className = isDark ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
    }
    updateThemeIcon();

    themeToggle.addEventListener('click', function () {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
      } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
      }
      updateThemeIcon();
    });
  }

  // ── Auto-dismiss flash alerts after 4 seconds ──────────
  document.querySelectorAll('.alert.alert-success, .alert.alert-info').forEach(function (alert) {
    setTimeout(function () {
      var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 4000);
  });

});
