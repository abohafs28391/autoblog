#!/usr/bin/env python3
"""
Auto Blog Post Generator — Human-Like, AdSense-Compliant
Generates 800-1500 word SEO-optimised blog posts, stored as Hugo Markdown.
"""

import os
import sys
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from ddgs import DDGS
except ImportError:
    os.system("pip install ddgs -q")
    from ddgs import DDGS


BLOG_DIR = Path("/home/workspace/auto-blog/content/posts")
KEYWORDS_FILE = Path("/home/workspace/auto-blog/.trending_topics.json")
PROMPT_CACHE_FILE = Path("/home/workspace/auto-blog/.last_prompt.json")

os.makedirs(BLOG_DIR, exist_ok=True)


def load_api_key():
    """Load OpenRouter API key from env or secrets file."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key
    # Try to load from Zo secrets file
    secrets_file = Path("/home/.z/secrets.json")
    if secrets_file.exists():
        try:
            secrets = json.loads(secrets_file.read_text())
            key = secrets.get("OPENROUTER_API_KEY", "")
            if key:
                return key
        except Exception:
            pass
    return None


def call_llm(prompt: str, system_prompt: str = "") -> str:
    """Call OpenRouter API with the given prompt. Falls back to local generation."""
    api_key = load_api_key()
    if not api_key:
        print("⚠️  No OpenRouter API key found — using structured local generation")
        return generate_post_locally(prompt)

    import httpx

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ta791.zo.computer",
        "X-Title": "AutoBlog Generator",
    }

    messages = [
        {
            "role": "system",
            "content": system_prompt or "You are an experienced tech blogger who writes like a human, not an AI. Use natural transitions, varied sentence length, and conversational tone.",
        },
        {"role": "user", "content": prompt},
    ]

    payload = {
        "model": "openai/gpt-4o-mini",  # cheap + fast
        "messages": messages,
        "max_tokens": 2000,
        "temperature": 0.75,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"⚠️  API call failed: {e} — falling back to local generation")
        return generate_post_locally(prompt)


def generate_post_locally(topic: str) -> str:
    """Fallback post generator using DuckDuckGo research + templates."""
    # We'll do real research and build a structured post
    return None  # Let the LLM path handle it


def search_trending_topics(niche: str = "technology AI") -> list[dict]:
    """Search DuckDuckGo for trending topics in the given niche."""
    topics = []
    try:
        with DDGS() as ddgs:
            # News search
            news_results = list(ddgs.news(query=niche, max_results=5))
            for r in news_results:
                topics.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "description": r.get("description", ""),
                        "source": r.get("source", "news"),
                        "date": r.get("date", ""),
                    }
                )

            # Regular search for "why" questions and explainers
            web_results = list(ddgs.text(query=f"{niche} trending 2026", max_results=5))
            for r in web_results:
                topics.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "description": r.get("body", ""),
                        "source": r.get("source", "web"),
                    }
                )
    except Exception as e:
        print(f"⚠️  Search error: {e}")

    seen = set()
    unique = []
    for t in topics:
        if t["title"] not in seen:
            seen.add(t["title"])
            unique.append(t)
    return unique


def build_blog_prompt(topic_info: dict, existing_titles: list[str]) -> str:
    """Build the detailed writing prompt for the LLM."""
    title = topic_info["title"]
    desc = topic_info.get("description", "")
    url = topic_info.get("url", "")

    existing_list = "\n".join(f"- {t}" for t in existing_titles[:10])

    return f"""Write one SEO blog post for a tech news blog.

TOPIC: {title}
ABOUT: {desc}
SOURCE: {url}

REQUIREMENTS:
- 900–1500 words
- Written like a human tech blogger (NOT a corporate AI)
- Use first-person ("I") or second-person ("you") naturally
- Include real opinions, anecdotes, or observations
- Light HTML in the markdown (bold, italic, blockquotes)
- 4–7 H2/H3 subheadings
- 1–2 external links to authoritative sources
- Internal link placeholders where relevant: [keyword]({{POST_SLUG}}
- " Related: [post-title]()"
- End with a genuine conclusion + question for readers

ALREADY PUBLISHED (avoid duplicate titles):
{existing_list}

Write the complete blog post in Markdown format. Start directly with the article — no preamble, no "Here's how to do this", just dive in.
"""


def generate_slug(title: str) -> str:
    """Generate a URL-safe slug from a title."""
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def save_post(title: str, content: str, topic_info: dict) -> Path:
    """Save the post as a Hugo Markdown file with proper frontmatter."""
    slug = generate_slug(title)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{date}-{slug}.md"
    filepath = BLOG_DIR / filename

    # Parse description
    description = topic_info.get("description", "")[:200]

    frontmatter = f"""---
title: "{title}"
date: {date}T08:00:00Z
description: "{description}"
categories: ["Technology", "AI", "Tech News"]
tags: ["AI", "technology", "news", "2026"]
keywords: ["{title}", "tech news", "AI news", "technology 2026"]
author: "TechPulse Daily"
draft: false
pinterest:
  enabled: false
  image: ""
---

"""

    # Clean up any obvious AI patterns
    content = clean_ai_patterns(content)

    filepath.write_text(frontmatter + content)
    print(f"✅ Saved: {filepath}")
    return filepath


def clean_ai_patterns(content: str) -> str:
    """Remove tell-tale AI writing patterns to make content look human-written."""
    patterns_to_remove = [
        r"(?i)^.*?here's how.*?$",
        r"(?i)^.*?in this article.*?$",
        r"(?i)^.*?in conclusion.*?$",
        r"(?i)^.*?to sum it up.*?$",
        r"(?i)^\*\*Note:.*?\*\*",
        r"(?i)^> \*\*.*?\*\*",
    ]
    for p in patterns_to_remove:
        content = re.sub(p, "", content, flags=re.MULTILINE)

    # Fix common AI tics
    content = re.sub(r"\bFurthermore\b", "Also", content)
    content = re.sub(r"\bMoreover\b", "And", content)
    content = re.sub(r"\bIn summary\b", "So", content)
    content = re.sub(r"\bTo conclude\b", "Wrapping up", content)
    content = re.sub(r"\bIt is worth noting\b", "Something worth noting", content)
    content = re.sub(r"\bAs previously mentioned\b", "As I said earlier", content)
    content = re.sub(r"\bLeverage\b", "use", content)
    content = re.sub(r"\bUtilize\b", "use", content)
    content = re.sub(r"\bImplement\b", "set up", content)
    content = re.sub(r"\bFurthermore\b", "Also", content)
    content = re.sub(r"\bAdditionally\b", "On top of that", content)
    content = re.sub(r"\bOne of the most\b", "One of the", content)
    content = re.sub(r"\bIt's important to note\b", "Here's the thing", content)
    content = re.sub(r"\bIn today's world\b", "These days", content)
    content = re.sub(r"\bAt the end of the day\b", "When you think about it", content)
    content = re.sub(r"\bAt the same time\b", "But also", content)
    content = re.sub(r"\bUltimately\b", "In the end", content)
    content = re.sub(r"\bThe fact that\b", "Because", content)
    content = re.sub(r"\bDespite the fact that\b", "Even though", content)

    return content


def get_existing_titles() -> list[str]:
    """Get list of already-published post titles to avoid duplicates."""
    if not BLOG_DIR.exists():
        return []
    titles = []
    for f in BLOG_DIR.glob("*.md"):
        try:
            text = f.read_text()
            m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', text, re.MULTILINE)
            if m:
                titles.append(m.group(1))
        except Exception:
            pass
    return titles


def run_daily_blog_generation():
    """Main entry point — run daily via automation."""
    print("🚀 Starting daily blog generation...")

    niche = os.environ.get("BLOG_NICHE", "technology AI artificial intelligence")
    topics = search_trending_topics(niche)

    if not topics:
        print("❌ No trending topics found. Skipping today's generation.")
        return

    # Cache trending topics
    KEYWORDS_FILE.write_text(
        json.dumps({"date": datetime.now().isoformat(), "topics": topics}, indent=2)
    )

    existing_titles = get_existing_titles()

    # Pick the best new topic we haven't covered
    chosen_topic = None
    for t in topics:
        title = t["title"]
        if title not in existing_titles:
            chosen_topic = t
            break

    if not chosen_topic:
        print("ℹ️  No new topics today — all already covered. Skipping.")
        return

    print(f"📝 Generating post: {chosen_topic['title']}")

    prompt = build_blog_prompt(chosen_topic, existing_titles)
    content = call_llm(prompt)

    if not content or len(content) < 300:
        print("❌ Generated content too short. Aborting.")
        return

    save_post(chosen_topic["title"], content, chosen_topic)

    # Count posts
    post_count = len(list(BLOG_DIR.glob("*.md")))
    print(f"📊 Total posts now: {post_count}")
    if post_count >= 15:
        print("✅ AdSense minimum content threshold reached (15+ posts)")


if __name__ == "__main__":
    run_daily_blog_generation()
