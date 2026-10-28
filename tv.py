#!/usr/bin/env python3
"""Read Best Buy's price for the LG 65" G6 OLED (OLED65G6WUA, SKU 6673119).

The product page blocks scripts, so this reads the search results page, which embeds the
same price data as JSON.
"""
import re
import urllib.request

SKU = "6673119"
NAME = 'LG 65" G6 OLED'
SEARCH = "https://www.bestbuy.com/site/searchpage.jsp?st=OLED65G6WUA"
PRODUCT = "https://www.bestbuy.com/site/6673119.p?skuId=6673119"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"


def price():
    """Return (current_price, regular_price) in dollars; raises if the page can't be read."""
    req = urllib.request.Request(SEARCH, headers={"User-Agent": UA, "Accept": "text/html", "Accept-Language": "en-US,en;q=0.9"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    for m in re.finditer(r'"price":\{"customerPrice":([0-9.]+)', page):
        block = page[m.start():m.start() + 6000]
        if f'"skuId":"{SKU}"' not in block[:400]:
            continue
        reg = re.search(r'"displayableRegularPrice":([0-9.]+)', block)
        return float(m.group(1)), float(reg.group(1)) if reg else None
    raise ValueError(f"SKU {SKU} price not found on Best Buy's search page")


if __name__ == "__main__":
    print(price())
