"""
Scheduler for Online Learning Trainer
Runs daily collection automatically

Usage:
    python schedule_online_learning.py
"""

import schedule
import time
from datetime import datetime
from online_learning_trainer import OnlineLearningTrainer
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Scheduler")


def run_daily_learning():
    """Run the daily learning cycle."""
    logger.info("\n" + "="*80)
    logger.info(f"SCHEDULED LEARNING CYCLE - {datetime.now()}")
    logger.info("="*80)
    
    try:
        trainer = OnlineLearningTrainer()
        result = trainer.run_daily_collection()
        
        if result['success']:
            logger.info("✓ Daily learning cycle completed successfully!")
            logger.info(f"  Articles: {result['articles']}")
            logger.info(f"  Processed: {result['processed']}")
            logger.info(f"  Systems updated: {result['systems_updated']}")
        else:
            logger.error(f"✗ Daily learning cycle failed: {result.get('error')}")
    
    except Exception as e:
        logger.error(f"✗ Error running daily learning: {e}")


def main():
    """Main scheduler."""
    print("\n" + "="*80)
    print(" ONLINE LEARNING SCHEDULER ".center(80))
    print("="*80)
    print("\nScheduling daily online learning...")
    print("  - Time: 3:00 AM daily")
    print("  - Collects news, weather, and other data")
    print("  - Feeds to your 27 AI learning systems")
    print("\nPress Ctrl+C to stop the scheduler\n")
    print("="*80 + "\n")
    
    # Schedule daily at 3 AM
    schedule.every().day.at("03:00").do(run_daily_learning)
    
    # For testing: also allow manual trigger every hour
    # schedule.every().hour.do(run_daily_learning)
    
    logger.info("Scheduler started. Waiting for scheduled time...")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    except KeyboardInterrupt:
        logger.info("\nScheduler stopped by user")
        print("\n✓ Scheduler stopped successfully")


if __name__ == "__main__":
    main()
