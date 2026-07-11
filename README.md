# Critical CSS Extractor

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> Extract above-the-fold CSS to boost Core Web Vitals and SEO rankings.

---

## What is Critical CSS?

Critical CSS contains only the styles needed to render content visible **above the fold** (the portion of the page users see on first load). Inlining this in the `<head>` eliminates render-blocking CSS requests, dramatically improving **First Contentful Paint (FCP)** and **Largest Contentful Paint (LCP)**.

### Why does this matter for SEO?

Google's **Core Web Vitals** are ranking signals. Render-blocking CSS is one of the most common causes of poor LCP scores. By extracting and inlining critical CSS, you:

- Reduce render-blocking resources
- Improve LCP / FCP by 20-50%
- Boost PageSpeed Insights and Lighthouse scores
- Directly improve Google Search ranking potential

---

## Features

- **CDTP rule tracking** — uses Chrome DevTools Protocol to extract real CSS rules (not computed inline styles), producing smaller, accurate output
- **Dual extraction** — auto-falls back to computed-style JS injection when CDTP isn't available
- **Multi-viewport** — captures critical CSS for mobile and desktop viewports, merging rules without duplicates
- **Batch mode** — process hundreds of URLs from a file
- **Inline output** — generate ready-to-paste `<style>` blocks for your templates
- **CI/CD ready** — zero-config CLI, easy to integrate into build pipelines

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Extract critical CSS
python main.py --url https://example.com

# Output written to critical.css
```

---

## CLI Reference

| Argument | Default | Description |
|----------|---------|-------------|
| `--url` | — | Target URL (required if no `--url-file`) |
| `--url-file` | — | File with URLs, one per line (`#` for comments) |
| `--mobile` | `375x812` | Mobile viewport dimensions |
| `--desktop` | `1366x900` | Desktop viewport dimensions |
| `--output` | `critical.css` | Output file (single URL) or directory (batch) |
| `--format` | `css` | Output format: `css` or `inline` (wraps in `<style>`) |
| `--method` | `auto` | Extraction: `cdtp`, `js`, or `auto` (try CDTP, fallback JS) |
| `--verbose`, `-v` | — | Enable debug logging |

### Examples

```bash
# Custom viewports
python main.py --url https://example.com --mobile 390x844 --desktop 1920x1080

# Output as inline <style> tag
python main.py --url https://example.com --format inline --output critical.html

# Batch process from file
python main.py --url-file urls.txt --output ./critical-css/ --verbose

# Force JS-only extraction
python main.py --url https://example.com --method js
```

### Batch mode

```
urls.txt
--------
https://example.com
https://example.com/about
https://example.com/contact
```

Each URL produces a separate `.css` file in the output directory:

```
critical-css/
  example_com.css
  example_com_about.css
  example_com_contact.css
```

---

## How It Works

1. **Launch** — headless Chromium via Playwright
2. **Navigate** — load the page at each configured viewport
3. **Track** — CDTP `CSS.startRuleUsageTracking` records every CSS rule applied during render
4. **Extract** — used rule ranges are sliced from their stylesheets
5. **Merge** — rules are deduplicated across viewports, preserving source order
6. **Output** — written as raw CSS or wrapped `<style>` block

If CDTP fails (some pages block DevTools), the tool falls back to injecting JavaScript that reads `getComputedStyle` for every visible element.

---

## Integration

### Webpack / Vite

Run as a pre-build step and inline the output into your HTML template.

### Django / Jinja / PHP

```html
<head>
  {% include 'critical.css' %}
  <link rel="stylesheet" href="/full.css" media="print" onload="this.media='all'">
</head>
```

### CI/CD (GitHub Actions)

```yaml
- name: Generate critical CSS
  run: |
    pip install -r requirements.txt
    playwright install chromium
    python main.py --url ${{ env.URL }} --output ./static/critical.css
```

---

## License

MIT
