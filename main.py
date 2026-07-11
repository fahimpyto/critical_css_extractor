import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright

logger = logging.getLogger("critical_css")

DEFAULT_VIEWPORTS: list[tuple[str, dict]] = [
    ("mobile", {"width": 375, "height": 812}),
    ("desktop", {"width": 1366, "height": 900}),
]

JS_FALLBACK = """
() => {
    var css = '';
    function safeClassName(el) {
        if (!el.className) return '';
        if (typeof el.className === 'string') return el.className;
        if (el.className.baseVal) return el.className.baseVal;
        return '';
    }
    function serialize(el) {
        var styles = window.getComputedStyle(el);
        var rule = '';
        for (var i = 0; i < styles.length; i++) {
            var prop = styles[i];
            var val = styles.getPropertyValue(prop);
            if (val && val !== 'initial' && val !== 'none') {
                rule += prop + ':' + val + ';';
            }
        }
        var cls = safeClassName(el).trim().replace(/\\s+/g, '.');
        var selector = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (cls ? '.' + cls : '');
        if (rule && selector.length < 200) {
            css += selector + '{' + rule + '}\\n';
        }
    }
    document.querySelectorAll('body, body *').forEach(function(el) {
        var r = el.getBoundingClientRect();
        if (r.top < window.innerHeight && r.bottom > 0) {
            serialize(el);
        }
    });
    return css;
}
"""


def extract_via_cdtp(page) -> str:
    cdp = page.context.new_cdp_session(page)
    cdp.send("CSS.enable")
    cdp.send("CSS.startRuleUsageTracking")
    page.reload(wait_until="networkidle")
    result = cdp.send("CSS.stopRuleUsageTracking")
    rule_usage = result.get("ruleUsage", [])

    sheets: dict[str, str] = {}
    for ru in rule_usage:
        sid = ru["styleSheetId"]
        if sid not in sheets:
            try:
                resp = cdp.send("CSS.getStyleSheetText", {"styleSheetId": sid})
                sheets[sid] = resp.get("text", "")
            except Exception:
                sheets[sid] = ""

    seen: set[str] = set()
    lines: list[str] = []
    for ru in rule_usage:
        if not ru.get("used"):
            continue
        text = sheets.get(ru["styleSheetId"], "")
        if not text:
            continue
        rule_text = text[ru["startOffset"] : ru["endOffset"]].strip()
        if rule_text and rule_text not in seen:
            seen.add(rule_text)
            lines.append(rule_text)
    return "\n".join(lines)


def extract_via_js(page) -> str:
    return page.evaluate(JS_FALLBACK)


def extract_for_viewport(page, viewport: dict, use_cdtp: bool) -> str:
    page.set_viewport_size(viewport)
    if use_cdtp:
        try:
            css = extract_via_cdtp(page)
            if css.strip():
                return css
        except Exception as e:
            logger.warning("CDTP failed: %s — falling back to JS", e)
    return extract_via_js(page)


def process_url(url: str, viewports: list[tuple[str, dict]], use_cdtp: bool = True) -> str:
    logger.info("Processing: %s", url)
    seen: set[str] = set()
    all_rules: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for vp_name, vp_size in viewports:
                logger.info("  Viewport: %s (%dx%d)", vp_name, vp_size["width"], vp_size["height"])
                context = browser.new_context(viewport=vp_size)
                page = context.new_page()
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    css = extract_for_viewport(page, vp_size, use_cdtp)
                    for rule in css.split("\n"):
                        s = rule.strip()
                        if s and s not in seen:
                            seen.add(s)
                            all_rules.append(s)
                finally:
                    context.close()
        finally:
            browser.close()

    return "\n".join(all_rules)


def format_output(css: str, fmt: str) -> str:
    if fmt == "inline":
        return f"<style>\n{css}\n</style>"
    return css


def parse_viewport(s: str) -> dict:
    m = re.match(r"(\d+)\s*x\s*(\d+)", s.strip().lower())
    if not m:
        raise ValueError(f"Invalid viewport format: {s!r} (expected WxH, e.g. 375x812)")
    return {"width": int(m.group(1)), "height": int(m.group(2))}


def sanitize_filename(url: str) -> str:
    name = url.replace("https://", "").replace("http://", "").rstrip("/")
    name = re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
    return name[:100] + ".css"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract critical CSS to improve Core Web Vitals and SEO rankings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s --url https://example.com
  %(prog)s --url https://example.com --mobile 390x844 --desktop 1920x1080
  %(prog)s --url-file urls.txt --output ./critical-css/
  %(prog)s --url https://example.com --format inline
        """,
    )
    parser.add_argument("--url", help="Target URL")
    parser.add_argument(
        "--url-file",
        help="File with URLs (one per line, # comments ignored) for batch processing",
    )
    parser.add_argument(
        "--mobile", default="375x812", help="Mobile viewport WxH (default: 375x812)"
    )
    parser.add_argument(
        "--desktop", default="1366x900", help="Desktop viewport WxH (default: 1366x900)"
    )
    parser.add_argument(
        "--output",
        default="critical.css",
        help="Output file or directory (default: critical.css)",
    )
    parser.add_argument(
        "--format",
        choices=["css", "inline"],
        default="css",
        help="Output format (default: css)",
    )
    parser.add_argument(
        "--method",
        choices=["cdtp", "js", "auto"],
        default="auto",
        help="Extraction method (default: auto — try CDTP, fallback JS)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if not args.url and not args.url_file:
        parser.error("Either --url or --url-file is required")

    viewports: list[tuple[str, dict]] = [
        ("mobile", parse_viewport(args.mobile)),
        ("desktop", parse_viewport(args.desktop)),
    ]

    use_cdtp = args.method in ("cdtp", "auto")

    urls: list[str] = []
    if args.url:
        urls.append(args.url)
    if args.url_file:
        with open(args.url_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)

    if not urls:
        logger.error("No URLs to process")
        sys.exit(1)

    batch = len(urls) > 1

    for url in urls:
        try:
            css = process_url(url, viewports, use_cdtp)
            output = format_output(css, args.format)

            if batch:
                out_dir = Path(args.output)
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / sanitize_filename(url)
            else:
                out_path = Path(args.output)
                out_path.parent.mkdir(parents=True, exist_ok=True)

            out_path.write_text(output, encoding="utf-8")
            logger.info("Written: %s", out_path)
        except Exception as e:
            logger.error("Failed %s: %s", url, e)

    logger.info("Done.")


if __name__ == "__main__":
    main()
