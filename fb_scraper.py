#!/usr/bin/env python3
"""
Facebook Scraper Module - STEALTH 2026 Edition
Persistent session + human behavior + proxy support
"""

import os
import json
import time
import random
import stat
import logging
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class StealthFacebookScraper:
    def __init__(self, email=None, password=None, headless=True, proxy=None):
        self.email = email
        self.password = password
        self.headless = headless
        self.proxy = proxy  # e.g. "http://user:pass@ip:port"

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # Persistent session file
        self.session_file = Path("data/facebook_session.json")
        self.session_file.parent.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        self.playwright = sync_playwright().start()

        launch_args = [
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-web-security",
            "--disable-extensions",
        ]

        browser_args = {
            "headless": self.headless,
            "args": launch_args,
            "ignore_default_args": ["--enable-automation"],
        }
        if self.proxy:
            browser_args["proxy"] = {"server": self.proxy}

        self.browser = self.playwright.chromium.launch(**browser_args)

        # Context with stealth settings
        context_options = {
            "viewport": {
                "width": random.randint(1280, 1366),
                "height": random.randint(720, 900),
            },
            "user_agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/134.0.0.0 Safari/537.36"
            ),
            "locale": "ar-EG",
            "timezone_id": "Africa/Cairo",
        }

        if self.session_file.exists() and self.session_file.stat().st_size > 100:
            try:
                with open(self.session_file) as f:
                    storage = json.load(f)
                    context_options["storage_state"] = storage
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not load session file: {e} — starting fresh session")

        self.context = self.browser.new_context(**context_options)
        self.page = self.context.new_page()

        # Hide Playwright fingerprints
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['ar-EG', 'en-US']});
        """)

        return self

    def __exit__(self, *args):
        if self.context:
            try:
                # Save session state
                self.context.storage_state(path=str(self.session_file))
                # Restrict session file permissions to owner-only (chmod 600)
                os.chmod(self.session_file, stat.S_IRUSR | stat.S_IWUSR)
                logger.info("Session saved with restricted permissions (600)")
            except Exception as e:
                logger.error(f"Failed to save session: {e}")
        if self.browser:
            try:
                self.browser.close()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception as e:
                logger.error(f"Error stopping playwright: {e}")

    def human_delay(self, min_sec=1.5, max_sec=4.0):
        time.sleep(random.uniform(min_sec, max_sec))

    def human_scroll(self, times=3):
        for _ in range(times):
            self.page.evaluate(f"window.scrollBy(0, {random.randint(400, 800)});")
            self.human_delay(1.2, 2.8)
            # Random mouse movement
            self.page.mouse.move(random.randint(100, 800), random.randint(100, 600))
            self.human_delay(0.3, 0.8)

    def login(self):
        """Login once — reuse session on subsequent runs."""
        if self.session_file.exists() and self.session_file.stat().st_size > 100:
            logger.info("✅ Session found — skipping login")
            return True

        if not self.email or not self.password:
            logger.error("No Facebook credentials provided")
            return False

        logger.info("🔑 First-time login...")
        try:
            self.page.goto("https://www.facebook.com", wait_until="networkidle", timeout=30000)
            self.human_delay()

            self.page.locator('input[name="email"]').fill(self.email)
            self.human_delay(0.8, 1.5)

            password_input = self.page.locator('input[name="pass"]')
            password_input.fill(self.password)
            self.human_delay(1, 2)
            password_input.press("Enter")
            self.human_delay(6, 10)

            # Save session with restricted permissions
            self.context.storage_state(path=str(self.session_file))
            os.chmod(self.session_file, stat.S_IRUSR | stat.S_IWUSR)
            logger.info("✅ Logged in and session saved")
            return True
        except PlaywrightTimeout:
            logger.error("Timeout during Facebook login")
            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def scrape_pages(self, page_urls, max_posts=15):
        """Scrape specific Facebook pages (safer than global search)."""
        all_posts = []
        for url in page_urls:
            try:
                logger.info(f"📄 Scraping: {url}")
                self.page.goto(url, wait_until="networkidle", timeout=30000)
                self.human_delay(2, 4)
                self.human_scroll(4)

                posts = self._extract_posts(max_posts)
                all_posts.extend(posts)
                logger.info(f"✅ Collected {len(posts)} posts from {url}")
            except PlaywrightTimeout:
                logger.error(f"Timeout scraping {url}")
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")

        return all_posts[: max_posts * len(page_urls)]

    def _extract_posts(self, max_posts):
        posts = []
        try:
            elements = self.page.locator(
                'div[data-pagelet^="FeedUnit"], div[role="article"]'
            ).all()
        except Exception as e:
            logger.error(f"Failed to locate post elements: {e}")
            return posts

        for el in elements[:max_posts]:
            try:
                text_parts = el.locator('div[dir="auto"]').all()
                text = " ".join(
                    [t.inner_text() for t in text_parts if t.is_visible()]
                )

                link = el.locator('a[href*="/posts/"], a[href*="/permalink/"]').first
                url = link.get_attribute("href") if link.count() > 0 else ""

                if url and url.startswith("/"):
                    url = f"https://www.facebook.com{url}"

                # Basic validation: must have text, valid URL, and enough content
                if text and url and url.startswith("https://") and len(text) > 30:
                    posts.append(
                        {
                            "url": url,
                            "text": text.strip()[:5000],  # Limit stored text size
                            "collected_at": datetime.now().isoformat(),
                        }
                    )
            except Exception as e:
                logger.debug(f"Skipping element due to error: {e}")
                continue

        return posts

    def search_keyword(self, keyword):
        """Search Facebook for a keyword."""
        try:
            logger.info(f"🔍 Searching for: {keyword}")
            # URL-encode the keyword properly
            import urllib.parse
            encoded = urllib.parse.quote(keyword)
            search_url = f"https://www.facebook.com/search/posts?q={encoded}"
            self.page.goto(search_url, wait_until="networkidle", timeout=30000)
            self.human_delay(2, 4)
            return True
        except PlaywrightTimeout:
            logger.error(f"Timeout searching for keyword: {keyword}")
            return False
        except Exception as e:
            logger.error(f"Search error for '{keyword}': {e}")
            return False

    def scroll_and_collect(self, max_posts=15, scroll_delay=2):
        """Scroll and collect posts from the current page."""
        all_posts = []
        try:
            self.human_scroll(5)
            posts = self._extract_posts(max_posts)
            all_posts.extend(posts)
            logger.info(f"✅ Collected {len(posts)} posts from search")
        except Exception as e:
            logger.error(f"Error collecting search posts: {e}")

        return all_posts[:max_posts]