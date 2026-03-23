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
