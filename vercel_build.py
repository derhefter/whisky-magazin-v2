#!/usr/bin/env python3
"""
Vercel Build Script — ersetzt 'python main.py --build-v2' auf Vercel.

Umgeht config.json-Prüfung (kein API-Key für statischen Build nötig)
und überspringt den git-Push am Ende.
"""
import os
import sys
from pathlib import Path

# Sicherstellen dass Vercel-Flag gesetzt ist (auch wenn nicht explizit übergeben)
os.environ["VERCEL"] = "1"

# Minimale Config — nur site-Felder werden beim Build gebraucht
VERCEL_CONFIG = {
    "site": {
        "name": "Whisky Magazin",
        "tagline": "Dein Guide für Whisky, Destillerien & Reisen",
        "base_url": "",
        "language": "de",
        "author": "Ellas"
    },
    "openai": {
        "api_key": "sk-vercel-build-placeholder",
        "model": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 4000
    },
    "affiliate_links": {
        "amazon_tag": "whiskyreise74-21",
        "tradedoubler_id": "2205846",
        "whisky_shops": [
            {
                "name": "Amazon Whisky",
                "url_template": "https://www.amazon.de/s?k={keyword}&tag=whiskyreise74-21",
                "priority": 1
            },
            {
                "name": "whisky.de",
                "url_template": "https://www.whisky.de/shop/search?q={keyword}",
                "priority": 2
            },
            {
                "name": "whic.de",
                "url_template": "https://whic.de/search?q={keyword}",
                "priority": 3
            }
        ],
        "travel_links": {
            "faehre": "https://clkde.tradedoubler.com/click?p=40187&a=2205846&g=23855448",
            "flug": "https://clk.tradedoubler.com/click?p=227718&a=2205846",
            "hotel": "https://www.whisky.reise/hotels/",
            "mietwagen": "https://www.whisky.reise/mietwagen/",
            "touren": "https://www.whisky.reise/touren/",
            "versicherung": "https://www.whisky.reise/reiseversicherung/",
            "wohnmobil": "https://www.whisky.reise/wohnmobil/"
        }
    },
    "content_settings": {
        "articles_per_run": 1,
        "min_word_count": 1200,
        "max_word_count": 2500
    }
}

print("\n  === Vercel Build ===")
print("  Starte site_builder_v2 mit eingebetteter Config...")

try:
    from site_builder_v2 import build_site_v2
    build_site_v2(VERCEL_CONFIG)
    print("\n  Vercel Build erfolgreich abgeschlossen.")
    sys.exit(0)
except Exception as e:
    print(f"\n  FEHLER im Vercel Build: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
