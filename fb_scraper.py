#!/usr/bin/env python3
"""
Facebook Scraper Module - STEALTH 2026 Edition
Persistent session + human behavior + proxy support
"""

import os
import json
import time
import random
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
        
        # Context مع stealth settings
        context_options = {
            "viewport": {"width": random.randint(1280, 1366), "height": random.randint(720, 900)},
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "locale": "ar-EG",
            "timezone_id": "Africa/Cairo",
        }
        
        if self.session_file.exists():
            with open(self.session_file) as f:
                storage = json.load(f)
                context_options["storage_state"] = storage
        
        self.context = self.browser.new_context(**context_options)
        self.page = self.context.new_page()
        
        # إخفاء Playwright fingerprints
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['ar-EG', 'en-US']});
        """)
        
        return self

    def __exit__(self, *args):
        if self.context:
            # حفظ الـ session
            self.context.storage_state(path=str(self.session_file))
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def human_delay(self, min_sec=1.5, max_sec=4.0):
        time.sleep(random.uniform(min_sec, max_sec))

    def human_scroll(self, times=3):
        for _ in range(times):
            self.page.evaluate("window.scrollBy(0, {});".format(random.randint(400, 800)))
            self.human_delay(1.2, 2.8)
            # حركة ماوس عشوائية
            self.page.mouse.move(random.randint(100, 800), random.randint(100, 600))
            self.human_delay(0.3, 0.8)

    def login(self):
        """تسجيل دخول مرة واحدة فقط"""
        if self.session_file.exists() and self.session_file.stat().st_size > 100:
            logger.info("✅ Session موجودة – تخطي تسجيل الدخول")
            return True

        logger.info("🔑 تسجيل دخول أول مرة...")
        self.page.goto("https://www.facebook.com", wait_until="networkidle")
        self.human_delay()

        self.page.locator('input[name="email"]').fill(self.email)
        self.human_delay(0.8, 1.5)
        self.page.locator('input[name="pass"]').fill(self.password)
        self.human_delay(1, 2)

        self.page.locator('button[name="login"]').click()
        self.human_delay(6, 10)

        # حفظ الـ session
        self.context.storage_state(path=str(self.session_file))
        logger.info("✅ تم تسجيل الدخول وحفظ الـ session")
        return True

    def scrape_pages(self, page_urls, max_posts=15):
        """الطريقة الأأمن: scraping صفحات محددة فقط (بدل البحث العام)"""
        all_posts = []
        for url in page_urls:
            try:
                logger.info(f"📄 جاري scraping: {url}")
                self.page.goto(url, wait_until="networkidle")
                self.human_delay(2, 4)
                self.human_scroll(4)

                posts = self._extract_posts(max_posts)
                all_posts.extend(posts)
                logger.info(f"✅ تم جمع {len(posts)} منشور من {url}")
            except Exception as e:
                logger.error(f"خطأ في {url}: {e}")
        
        return all_posts[:max_posts * len(page_urls)]

    def _extract_posts(self, max_posts):
        posts = []
        elements = self.page.locator('div[data-pagelet^="FeedUnit"], div[role="article"]').all()
        
        for el in elements[:max_posts]:
            try:
                text = " ".join([t.inner_text() for t in el.locator('div[dir="auto"]').all() if t.is_visible()])
                link = el.locator('a[href*="/posts/"], a[href*="/permalink/"]').first
                url = link.get_attribute("href") if link.count() > 0 else ""
                if url and url.startswith("/"):
                    url = f"https://www.facebook.com{url}"
                
                if text and url and len(text) > 30:
                    posts.append({
                        "url": url,
                        "text": text.strip(),
                        "collected_at": datetime.now().isoformat()
                    })
            except:
                continue
        return posts

    def search_keyword(self, keyword):
        """البحث العام عن كلمة مفتاحية"""
        try:
            logger.info(f"🔍 جاري البحث عن: {keyword}")
            search_url = f"https://www.facebook.com/search/posts?q={keyword}"
            self.page.goto(search_url, wait_until="networkidle")
            self.human_delay(2, 4)
            return True
        except Exception as e:
            logger.error(f"خطأ في البحث: {e}")
            return False
            
    def scroll_and_collect(self, max_posts=15, scroll_delay=2):
        """التمرير وجمع المنشورات من صفحة البحث"""
        all_posts = []
        try:
            self.human_scroll(5)  # Scroll a few times to load posts
            posts = self._extract_posts(max_posts)
            all_posts.extend(posts)
            logger.info(f"✅ تم جمع {len(posts)} منشور من البحث")
        except Exception as e:
            logger.error(f"خطأ أثناء جمع منشورات البحث: {e}")
            
        return all_posts[:max_posts]