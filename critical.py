from playwright.sync_api import sync_playwright

URL = "https://test.alleducationboardresults.com/"

VIEWPORTS = [
    {"width": 375, "height": 812},
    {"width": 1366, "height": 900},
]

OUTPUT = "critical.css"

JS = """
() => {
    let css = '';

    function safeClassName(el) {
        if (!el.className) return '';
        if (typeof el.className === 'string') return el.className;
        if (el.className.baseVal) return el.className.baseVal;
        return '';
    }

    function serialize(el) {
        const styles = window.getComputedStyle(el);
        let rule = '';
        for (let i = 0; i < styles.length; i++) {
            const prop = styles[i];
            const val = styles.getPropertyValue(prop);
            if (val && val !== 'initial' && val !== 'none') {
                rule += `${prop}:${val};`;
            }
        }

        const cls = safeClassName(el).trim().replace(/\\s+/g, '.');
        const selector =
            el.tagName.toLowerCase() +
            (el.id ? '#' + el.id : '') +
            (cls ? '.' + cls : '');

        if (rule && selector.length < 200) {
            css += `${selector}{${rule}}\\n`;
        }
    }

    document.querySelectorAll('body, body *').forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.top < window.innerHeight && r.bottom > 0) {
            serialize(el);
        }
    });

    return css;
}
"""

all_css = set()

with sync_playwright() as p:
    browser = p.chromium.launch()

    for vp in VIEWPORTS:
        context = browser.new_context(viewport=vp)
        page = context.new_page()
        page.goto(URL, wait_until="networkidle")

        css = page.evaluate(JS)
        all_css.add(css)

        context.close()

    browser.close()

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(all_css))

print(f"✅ Critical CSS generated successfully → {OUTPUT}")
