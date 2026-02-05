from playwright.sync_api import sync_playwright

url = "https://test.alleducationboardresults.com/"
viewports = {
    'mobile' : {"width" : 375, "height" : 812} ,
    'desktop' : {"width" : 1366, "height": 900}
}

def get_critical_css(page, client):
    client.send("CSS.enable")
    client.send("CSS.startRuleUsageTracking")
    page.reload(wait_untill = "networkidle")
    usage = client.send("CSS.stopRuleUsageTracking")
    used_rules_by_sheet = {}