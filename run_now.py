import logging
from main import HackathonTracker
from unittest.mock import patch
from datetime import datetime

logging.basicConfig(level=logging.INFO)

print("Starting manual test run...")
tracker = HackathonTracker()

# We need to bypass the time check and the last_run check.
# The time check looks for hour >= 21 and minute >= 30.
fake_now = datetime(2026, 4, 22, 22, 0, 0)

with patch('main.datetime') as mock_datetime:
    mock_datetime.now.return_value = fake_now
    mock_datetime.strptime = datetime.strptime
    mock_datetime.combine = datetime.combine
    
    # Also temporarily remove the last_run_file so it doesn't skip
    if tracker.last_run_file.exists():
        tracker.last_run_file.unlink()
        
    tracker.run_daily_check()

print("Manual run complete.")
