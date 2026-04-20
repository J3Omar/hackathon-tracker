#!/usr/bin/env python3
"""
Scheduler Script
Runs the hackathon tracker at a specific time daily
"""

import schedule
import time
import logging
from datetime import datetime
from main import HackathonTracker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_tracker():
    """Wrapper function to run the tracker"""
    logger.info("Scheduled task triggered!")
    tracker = HackathonTracker()
    tracker.run_daily_check()


def main():
    """Main scheduler loop"""
    # Schedule the task for 10 PM daily
    schedule.every().day.at("22:00").do(run_tracker)
    
    logger.info("=" * 60)
    logger.info("Hackathon Tracker Scheduler Started")
    logger.info(f"Current time: {datetime.now()}")
    logger.info("Scheduled to run daily at 22:00 (10 PM)")
    logger.info("=" * 60)
    
    # Run immediately for testing (comment out in production)
    # logger.info("Running immediate test check...")
    # run_tracker()
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()
