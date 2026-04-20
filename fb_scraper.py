#!/usr/bin/env python3
"""
Facebook Scraper Module
Uses Playwright to automate Facebook browsing and collect posts
"""

import os
import json
import time
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class FacebookScraper:
    def __init__(self, email, password, headless=True):
        self.email = email
        self.password = password
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        
    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = self.context.new_page()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def login(self):
        """Login to Facebook"""
        try:
            logger.info("Attempting to login to Facebook...")
            self.page.goto("https://www.facebook.com", wait_until="networkidle")
            time.sleep(2)
            
            # Fill email
            email_input = self.page.locator('input[name="email"]')
            email_input.fill(self.email)
            time.sleep(1)
            
            # Fill password
            password_input = self.page.locator('input[name="pass"]')
            password_input.fill(self.password)
            time.sleep(1)
            
            # Click login button
            login_button = self.page.locator('button[name="login"]')
            login_button.click()
            
            # Wait for navigation
            time.sleep(5)
            
            # Check if login was successful
            if "login" in self.page.url.lower() or "checkpoint" in self.page.url.lower():
                logger.error("Login failed - possible CAPTCHA or security check")
                return False
            
            logger.info("Login successful!")
            return True
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    def search_keyword(self, keyword):
        """Search for a keyword on Facebook"""
        try:
            logger.info(f"Searching for keyword: {keyword}")
            search_url = f"https://www.facebook.com/search/posts?q={keyword}"
            self.page.goto(search_url, wait_until="networkidle")
            time.sleep(3)
            return True
        except Exception as e:
            logger.error(f"Search error: {e}")
            return False
    
    def scroll_and_collect(self, max_posts=20, scroll_delay=2):
        """Scroll the page and collect posts"""
        posts = []
        seen_urls = set()
        
        try:
            logger.info(f"Collecting up to {max_posts} posts...")
            
            for _ in range(10):  # Max 10 scrolls
                # Get all post elements
                post_elements = self.page.locator('div[data-pagelet^="FeedUnit"]').all()
                
                for element in post_elements:
                    if len(posts) >= max_posts:
                        break
                    
                    try:
                        # Extract post text
                        text_elements = element.locator('div[dir="auto"]').all()
                        text = " ".join([el.inner_text() for el in text_elements if el.is_visible()])
                        
                        # Extract post link
                        link_element = element.locator('a[href*="/posts/"], a[href*="/permalink/"]').first
                        if link_element.count() > 0:
                            href = link_element.get_attribute('href')
                            if href and href not in seen_urls:
                                full_url = href if href.startswith('http') else f"https://www.facebook.com{href}"
                                
                                post = {
                                    'url': full_url,
                                    'text': text.strip(),
                                    'collected_at': datetime.now().isoformat()
                                }
                                
                                posts.append(post)
                                seen_urls.add(href)
                                logger.info(f"Collected post {len(posts)}/{max_posts}")
                    
                    except Exception as e:
                        logger.debug(f"Error extracting post: {e}")
                        continue
                
                if len(posts) >= max_posts:
                    break
                
                # Scroll down
                self.page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(scroll_delay)
            
            logger.info(f"Total posts collected: {len(posts)}")
            return posts
            
        except Exception as e:
            logger.error(f"Error during scrolling: {e}")
            return posts
    
    def scrape_page(self, page_url, max_posts=20):
        """Scrape posts from a specific Facebook page"""
        try:
            logger.info(f"Scraping page: {page_url}")
            self.page.goto(page_url, wait_until="networkidle")
            time.sleep(3)
            
            return self.scroll_and_collect(max_posts=max_posts)
        
        except Exception as e:
            logger.error(f"Error scraping page {page_url}: {e}")
            return []


def test_scraper():
    """Test the scraper with credentials from .env"""
    from dotenv import load_dotenv
    load_dotenv()
    
    email = os.getenv('FB_EMAIL')
    password = os.getenv('FB_PASSWORD')
    
    if not email or not password:
        print("Please set FB_EMAIL and FB_PASSWORD in .env file")
        return
    
    with FacebookScraper(email, password, headless=False) as scraper:
        if scraper.login():
            posts = scraper.search_keyword("hackathon")
            print(f"Found {len(posts)} posts")
            for post in posts[:3]:
                print(f"\n{post['url']}")
                print(f"{post['text'][:200]}...")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_scraper()
