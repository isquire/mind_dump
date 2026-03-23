#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# setup_assets.sh — Download all frontend vendor assets locally.
# Run once before first launch. Requires curl or wget.
# After this script completes, the app has NO runtime internet dependencies.
# ──────────────────────────────────────────────────────────────────────────────
set -e

VENDOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/static/vendor"
mkdir -p "$VENDOR_DIR"

# ── Versions ─────────────────────────────────────────────
BOOTSTRAP_VERSION="5.3.3"
BI_VERSION="1.11.3"
QUILL_VERSION="1.3.7"

# ── Download helper ───────────────────────────────────────
download() {
  local url="$1"
  local dest="$2"
  if [ -f "$dest" ]; then
    echo "  [skip] $(basename "$dest") already exists"
    return
  fi
  echo "  [get]  $(basename "$dest")"
  if command -v curl &>/dev/null; then
    curl -fsSL "$url" -o "$dest"
  elif command -v wget &>/dev/null; then
    wget -q "$url" -O "$dest"
  else
    echo "ERROR: neither curl nor wget found. Install one and retry."
    exit 1
  fi
}

echo "Downloading Bootstrap ${BOOTSTRAP_VERSION}…"
download \
  "https://cdn.jsdelivr.net/npm/bootstrap@${BOOTSTRAP_VERSION}/dist/css/bootstrap.min.css" \
  "$VENDOR_DIR/bootstrap.min.css"
download \
  "https://cdn.jsdelivr.net/npm/bootstrap@${BOOTSTRAP_VERSION}/dist/js/bootstrap.bundle.min.js" \
  "$VENDOR_DIR/bootstrap.bundle.min.js"

echo "Downloading Bootstrap Icons ${BI_VERSION}…"
download \
  "https://cdn.jsdelivr.net/npm/bootstrap-icons@${BI_VERSION}/font/bootstrap-icons.min.css" \
  "$VENDOR_DIR/bootstrap-icons.min.css"

# Bootstrap Icons font files (referenced relative to the CSS)
mkdir -p "$VENDOR_DIR/fonts"
download \
  "https://cdn.jsdelivr.net/npm/bootstrap-icons@${BI_VERSION}/font/fonts/bootstrap-icons.woff2" \
  "$VENDOR_DIR/fonts/bootstrap-icons.woff2"
download \
  "https://cdn.jsdelivr.net/npm/bootstrap-icons@${BI_VERSION}/font/fonts/bootstrap-icons.woff" \
  "$VENDOR_DIR/fonts/bootstrap-icons.woff"

# Fix font path in CSS to point at local fonts/
if [ -f "$VENDOR_DIR/bootstrap-icons.min.css" ]; then
  # Replace jsdelivr font URL with relative local path
  sed -i 's|https://cdn\.jsdelivr\.net/npm/bootstrap-icons@[^/]*/font/fonts/|fonts/|g' \
    "$VENDOR_DIR/bootstrap-icons.min.css"
fi

echo "Downloading Quill ${QUILL_VERSION}…"
download \
  "https://cdn.quilljs.com/${QUILL_VERSION}/quill.min.js" \
  "$VENDOR_DIR/quill.min.js"
download \
  "https://cdn.quilljs.com/${QUILL_VERSION}/quill.snow.css" \
  "$VENDOR_DIR/quill.snow.css"

echo ""
echo "✓ All vendor assets downloaded to static/vendor/"
echo "  You can now run the app with: bash run.sh"
