#!/usr/bin/env python3
"""
Main Hackathon Tracker Script
Orchestrates the entire workflow: scraping -> analysis -> notification
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from fb_scraper import StealthFacebookScraper
from gemma_analyzer import GemmaAnalyzer
from telegram_notifier import TelegramNotifier
from email_notifier import EmailNotifier


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/tracker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HackathonTracker:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        try:
            with open('config/config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            logger.critical("config/config.json not found — run setup.sh first")
            raise
        except json.JSONDecodeError as e:
            logger.critical(f"config/config.json is malformed: {e}")
            raise
        
        # Initialize components
        self.fb_email = os.getenv('FB_EMAIL')
        self.fb_password = os.getenv('FB_PASSWORD')
        self.fb_proxy = os.getenv('FB_PROXY')
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.lm_studio_url = os.getenv('LM_STUDIO_URL')
        
        # Email Configuration
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = os.getenv('SMTP_PORT', '587')
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.target_emails = os.getenv('TARGET_EMAILS')
        
        # Parse search keywords and target pages
        self.search_keywords = [k.strip() for k in os.getenv('SEARCH_KEYWORDS', '').split(',')]
        self.target_pages = [p.strip() for p in os.getenv('TARGET_PAGES', '').split(',') if p.strip()]
        self.location_keywords = [l.strip() for l in os.getenv('LOCATION_KEYWORDS', '').split(',')]
        
        # Initialize modules
        self.analyzer = GemmaAnalyzer(self.lm_studio_url, self.location_keywords)
        self.notifier = TelegramNotifier(self.telegram_token, self.telegram_chat_id)
        self.email_notifier = EmailNotifier(
            self.smtp_server, self.smtp_port, self.smtp_username, self.smtp_password, self.target_emails
        )
        
        # Data files
        self.seen_posts_file = Path(self.config['data']['seen_posts_file'])
        self.posts_file = Path(self.config['data']['posts_file'])
        self.last_run_file = Path('data/last_run.txt')
        
        # Create data directory if it doesn't exist
        self.seen_posts_file.parent.mkdir(exist_ok=True)
        
    def load_seen_posts(self):
        """Load the list of already seen post URLs"""
        if self.seen_posts_file.exists():
            with open(self.seen_posts_file, 'r') as f:
                return set(json.load(f))
        return set()
    
    def save_seen_posts(self, seen_posts):
        """Save the list of seen post URLs"""
        with open(self.seen_posts_file, 'w') as f:
            json.dump(list(seen_posts), f, indent=2)
    
    def scrape_posts(self):
        """Scrape posts from Facebook"""
        all_posts = []
        
        if not self.target_pages and not self.search_keywords:
            logger.warning("No TARGET_PAGES or SEARCH_KEYWORDS defined in .env.")
            return []
            
        with StealthFacebookScraper(
            self.fb_email, 
            self.fb_password, 
            headless=self.config['scraping']['headless'],
            proxy=self.fb_proxy
        ) as scraper:
            
            # Login
            if not scraper.login():
                logger.error("Failed to login to Facebook")
                self.notifier.send_error_notification("فشل تسجيل الدخول إلى فيسبوك")
                self.email_notifier.send_error_notification("فشل تسجيل الدخول إلى فيسبوك")
                return []
            
            # Method 1: Search by keywords
            if self.search_keywords:
                logger.info("Searching by keywords...")
                for keyword in self.search_keywords:
                    if scraper.search_keyword(keyword):
                        posts = scraper.scroll_and_collect(
                            max_posts=self.config['scraping']['max_posts_per_page'],
                            scroll_delay=self.config['scraping']['scroll_delay']
                        )
                        all_posts.extend(posts)
            
            # Method 2: Scrape specific pages
            if self.target_pages:
                logger.info("Scraping target pages...")
                pages_posts = scraper.scrape_pages(
                    self.target_pages,
                    max_posts=self.config['scraping']['max_posts_per_page']
                )
                all_posts.extend(pages_posts)
        
        # Remove duplicates based on URL
        unique_posts = {post['url']: post for post in all_posts}.values()
        logger.info(f"Total unique posts collected: {len(unique_posts)}")
        
        return list(unique_posts)
    
    def analyze_posts(self, posts):
        """Analyze posts using Gemma 3"""
        analyzed_posts = []
        
        for i, post in enumerate(posts, 1):
            logger.info(f"Analyzing post {i}/{len(posts)}")
            
            analysis = self.analyzer.analyze_post(post['text'])
            
            if analysis:
                post['analysis'] = analysis
                analyzed_posts.append(post)
            else:
                logger.warning(f"Failed to analyze post: {post['url']}")
        
        return analyzed_posts
    
    def filter_new_posts(self, posts, seen_posts):
        """Filter out posts that have already been seen"""
        new_posts = [p for p in posts if p['url'] not in seen_posts]
        logger.info(f"New posts: {len(new_posts)} out of {len(posts)}")
        return new_posts
    
    def run_daily_check(self, wait_until_time=None, skip_scraping=False):
        """Run the complete daily check workflow"""
        try:
            now = datetime.now()
            today = now.strftime('%Y-%m-%d')
            
            # Check if already run today
            if self.last_run_file.exists() and not skip_scraping:
                with open(self.last_run_file, 'r') as f:
                    last_run = f.read().strip()
                if last_run == today:
                    logger.info("Already ran today. Exiting.")
                    return
            
            # Ensure it only runs at night (after 9:30 PM = 21:30)
            if now.hour < 21 or (now.hour == 21 and now.minute < 30):
                if not skip_scraping:
                    logger.info("Too early. Waiting until 9:30 PM to run the check.")
                    return
            
            logger.info("=" * 50)
            logger.info("Starting daily hackathon check...")
            logger.info(f"Time: {now}")
            logger.info("=" * 50)
            
            # Load seen posts
            seen_posts = self.load_seen_posts()
            logger.info(f"Previously seen posts: {len(seen_posts)}")
            
            raw_posts_file = Path('data/raw_new_posts.json')
            
            if skip_scraping:
                logger.info("\n[1-2/4] Skipping scraping, loading from raw_new_posts.json...")
                if raw_posts_file.exists():
                    with open(raw_posts_file, 'r', encoding='utf-8') as f:
                        new_posts = json.load(f)
                    all_posts = new_posts # For updating seen_posts later
                else:
                    logger.error("raw_new_posts.json not found! Cannot skip scraping.")
                    return
            else:
                # Step 1: Scrape posts
                logger.info("\n[1/4] Scraping Facebook posts...")
                all_posts = self.scrape_posts()
                
                if not all_posts:
                    logger.warning("No posts found")
                    self.notifier.send_message("⚠️ لم يتم العثور على منشورات جديدة")
                    self.email_notifier.send_error_notification("لم يتم العثور على أي منشورات جديدة من فيسبوك اليوم.")
                    return
                
                # Step 2: Filter new posts
                logger.info("\n[2/4] Filtering new posts...")
                new_posts = self.filter_new_posts(all_posts, seen_posts)
                
                if not new_posts:
                    logger.info("No new posts to analyze")
                    self.notifier.send_message("✅ تم فحص المنشورات - لا توجد منشورات جديدة")
                    self.email_notifier.send_error_notification("تم فحص المنشورات - لا توجد منشورات جديدة اليوم.")
                    return
                
                # Backup new_posts to disk in case analysis fails
                logger.info(f"Saving {len(new_posts)} raw posts to disk for backup...")
                with open(raw_posts_file, 'w', encoding='utf-8') as f:
                    json.dump(new_posts, f, indent=2, ensure_ascii=False)
            
            # Step 3: Analyze posts
            logger.info(f"\n[3/4] Analyzing {len(new_posts)} new posts with Gemma 3...")
            analyzed_posts = self.analyze_posts(new_posts)
            
            # Step 4: Filter relevant hackathons
            logger.info("\n[4/4] Filtering relevant hackathons...")
            relevant_hackathons = self.analyzer.filter_relevant_hackathons(
                analyzed_posts,
                min_confidence=self.config['filters']['min_confidence'],
                days_ahead=self.config['filters']['days_ahead']
            )
            
            # Wait until the specified time to send notifications
            if wait_until_time:
                import time
                target_time = datetime.strptime(wait_until_time, "%H:%M").time()
                now = datetime.now()
                target_datetime = datetime.combine(now.date(), target_time)
                
                if now < target_datetime:
                    sleep_seconds = (target_datetime - now).total_seconds()
                    logger.info(f"\n⏳ Waiting {sleep_seconds:.0f} seconds until {wait_until_time} to send notifications...")
                    time.sleep(sleep_seconds)
            
            # Step 5: Send notifications
            if relevant_hackathons:
                logger.info(f"\n✅ Found {len(relevant_hackathons)} relevant hackathons!")
                self.notifier.send_daily_summary(relevant_hackathons)
                self.email_notifier.send_daily_summary(relevant_hackathons)
                
                # Save results
                with open(self.posts_file, 'w', encoding='utf-8') as f:
                    json.dump(relevant_hackathons, f, indent=2, ensure_ascii=False)
            else:
                logger.info("\n📭 No relevant hackathons found")
                self.notifier.send_message("📭 تم فحص المنشورات - لا توجد هاكاثونات ذات صلة")
                self.email_notifier.send_daily_summary([])
            
            # Update seen posts
            for post in all_posts:
                seen_posts.add(post['url'])
            self.save_seen_posts(seen_posts)
            
            # Update last run date
            with open(self.last_run_file, 'w') as f:
                f.write(today)
            
            logger.info("\n" + "=" * 50)
            logger.info("Daily check completed successfully!")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"Error during daily check: {e}", exc_info=True)
            error_msg = f"حدث خطأ أثناء التحقق اليومي:\n{str(e)}"
            self.notifier.send_error_notification(error_msg)
            self.email_notifier.send_error_notification(error_msg)


def main():
    """Main entry point"""
    import argparse
    parser = argparse.ArgumentParser(description="Hackathon Tracker")
    parser.add_argument("--wait-until", type=str, help="Time to wait until sending notifications (e.g., 22:00)", default=None)
    args = parser.parse_args()

    tracker = HackathonTracker()
    tracker.run_daily_check(wait_until_time=args.wait_until)


if __name__ == "__main__":
    main()
