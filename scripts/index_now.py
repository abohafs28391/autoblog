#!/usr/bin/env python3
"""
index_now.py — Submit new blog posts to IndexNow API for instant Bing/Yandex indexing.
Also prints sitemap-ready URLs for Google Search Console manual submission.
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone

try:
    import httpx
except ImportError:
    os.system("pip install httpx -q")
    import httpx


INDEXNOW_KEY_FILE = Path("/home/workspace/auto-blog/.indexnow_key.txt")
INDEXNOW_KEY_API_FILE = Path("/home/workspace/auto-blog/.indexnow_key_api.txt")
BLOG_DIR = Path("/home/workspace/auto-blog/content/posts")
BASE_URL = os.environ.get("BLOG_BASE_URL", "https://yourblog.netlify.app")


def generate_indexnow_keys(site_url: str) -> tuple[str, str]:
    """Generate and save IndexNow key + key-api file for the given site URL."""
    key = hashlib.sha256(f"{site_url}{time.time()}".encode()).hexdigest()[:32]
    key_api = f"https://{BASE_URL}/{key}.txt"
    INDEXNOW_KEY_FILE.write_text(key)
    INDEXNOW_KEY_API_FILE.write_text(key_api)
    print(f"✅ IndexNow keys generated — submit these to Bing Webmaster Tools:")
    print(f"   Key file URL: {key_api}")
    print(f"   Key value: {key}")
    return key, key_api


def submit_to_indexnow(urls: list[str], site_url: str = BASE_URL, key: str = "") -> bool:
    """
    Submit URLs to IndexNow (Bing + Yandex + other participating engines).
    Requires key to be verified first via Bing Webmaster Tools.
    """
    if not key:
        # Try loading existing key
        if INDEXNOW_KEY_FILE.exists():
            key = INDEXNOW_KEY_FILE.read_text().strip()
        else:
            print("⚠️  No IndexNow key found — skipping IndexNow submission")
            print(f"   Add your site to Bing Webmaster Tools first: https://bing.com/webmasters")
            return False

    endpoint = "https://www.bing.com/indexnow"

    payload = {
        "key": key,
        "keyLocation": f"{site_url}/{key}.txt",
        "urlList": urls,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(endpoint, json=payload)
            if resp.status_code in (200, 201, 202):
                print(f"✅ IndexNow: submitted {len(urls)} URL(s) successfully")
                return True
            else:
                print(f"⚠️  IndexNow returned {resp.status_code}: {resp.text[:200]}")
                return False
    except Exception as e:
        print(f"❌ IndexNow error: {e}")
        return False


def generate_sitemap_urls() -> list[dict]:
    """Generate sitemap entries for all published posts."""
    if not BLOG_DIR.exists():
        return []

    entries = []
    for f in sorted(BLOG_DIR.glob("*.md")):
        try:
            text = f.read_text()
            # Extract date from filename or frontmatter
            date_match = f.name[:10]  # YYYY-MM-DD from filename
            slug = f.stem[11:]  # Remove date prefix
            post_url = f"{BASE_URL}/{slug}/"
            entries.append({
                "loc": post_url,
                "lastmod": date_match,
                "changefreq": "weekly",
                "priority": "0.7",
            })
        except Exception as e:
            print(f"⚠️  Error reading {f}: {e}")
    return entries


def write_sitemap_xml(urls: list[dict], output_path: Path):
    """Write a standard XML sitemap."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{u['loc']}</loc>")
        lines.append(f"    <lastmod>{u['lastmod']}</lastmod>")
        lines.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        lines.append(f"    <priority>{u['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")

    output_path.write_text("\n".join(lines))
    print(f"✅ Sitemap written: {output_path} ({len(urls)} URLs)")


def submit_to_google_search_console(url: str) -> str:
    """Generate the URL Inspection link for GSC."""
    encoded = httpx.URL(url).path
    return f"https://search.google.com/search-console?url={url}& resource_id={BASE_URL}"


def run_indexing():
    """Main entry — submit all new posts to IndexNow + update sitemap."""
    print("📡 Running indexing pipeline...")

    urls = generate_sitemap_urls()
    if not urls:
        print("❌ No posts found. Run generate_post.py first.")
        return

    sitemap_urls = [u["loc"] for u in urls]

    # Write local sitemap
    sitemap_path = Path("/home/workspace/auto-blog/public/sitemap.xml")
    sitemap_path.parent.mkdir(parents=True, exist_ok=True)
    write_sitemap_xml(urls, sitemap_path)

    # Submit to IndexNow
    key = INDEXNOW_KEY_FILE.read_text().strip() if INDEXNOW_KEY_FILE.exists() else ""
    submit_to_indexnow(sitemap_urls, key=key)

    # Print GSC-ready links
    print("\n🔗 Google Search Console URL Inspection links:")
    for u in sitemap_urls[-5:]:
        print(f"   {u}")

    print(f"\n📊 Total URLs in sitemap: {len(urls)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "generate-keys":
        generate_indexnow_keys(sys.argv[2] if len(sys.argv) > 2 else BASE_URL)
    else:
        run_indexing()
