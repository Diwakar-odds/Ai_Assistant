"""
Date-Based Log Management Utilities

This script provides utilities for managing date-based logs:
- View logs by date
- Archive old logs
- Clean up logs older than X days
- Get log statistics by date
"""

from pathlib import Path
from datetime import datetime, timedelta
import shutil
import json
import os

class LogManager:
    """Manage date-based log directories"""
    
    def __init__(self, base_dir='logs'):
        self.base_dir = Path(base_dir)
    
    def list_log_dates(self):
        """List all available log dates"""
        dates = []
        for item in self.base_dir.glob('20??-??-??'):
            if item.is_dir():
                dates.append(item.name)
        return sorted(dates, reverse=True)
    
    def get_logs_for_date(self, date_str):
        """Get all logs for a specific date
        
        Args:
            date_str: Date in YYYY-MM-DD format
        """
        date_folder = self.base_dir / date_str
        if not date_folder.exists():
            return None
        
        logs = {}
        for category in date_folder.iterdir():
            if category.is_dir():
                logs[category.name] = list(category.glob('*'))
        
        return logs
    
    def get_log_stats(self, date_str=None):
        """Get statistics for logs
        
        Args:
            date_str: Specific date or None for all dates
        """
        if date_str:
            dates = [date_str]
        else:
            dates = self.list_log_dates()
        
        stats = {}
        for date in dates:
            date_folder = self.base_dir / date
            if not date_folder.exists():
                continue
            
            total_size = 0
            file_count = 0
            
            for log_file in date_folder.rglob('*'):
                if log_file.is_file():
                    total_size += log_file.stat().st_size
                    file_count += 1
            
            stats[date] = {
                'total_size_mb': total_size / (1024 * 1024),
                'file_count': file_count,
                'path': str(date_folder)
            }
        
        return stats
    
    def archive_logs(self, date_str, archive_dir='logs/archives'):
        """Archive logs for a specific date
        
        Args:
            date_str: Date in YYYY-MM-DD format
            archive_dir: Directory to store archives
        """
        date_folder = self.base_dir / date_str
        if not date_folder.exists():
            print(f"❌ No logs found for {date_str}")
            return False
        
        archive_path = Path(archive_dir)
        archive_path.mkdir(parents=True, exist_ok=True)
        
        archive_file = archive_path / f'logs_{date_str}.tar.gz'
        
        # Create archive
        print(f"📦 Archiving {date_str} -> {archive_file}")
        shutil.make_archive(
            str(archive_file.with_suffix('')),
            'gztar',
            root_dir=self.base_dir,
            base_dir=date_str
        )
        
        print(f"✅ Archive created: {archive_file}")
        return True
    
    def cleanup_old_logs(self, days_to_keep=30, dry_run=True):
        """Delete logs older than specified days
        
        Args:
            days_to_keep: Number of days to keep
            dry_run: If True, only show what would be deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        print(f"🧹 Cleanup logs older than {days_to_keep} days (before {cutoff_str})")
        print(f"   Mode: {'DRY RUN' if dry_run else 'DELETE'}\n")
        
        deleted_count = 0
        total_size = 0
        
        for date_folder in self.base_dir.glob('20??-??-??'):
            try:
                folder_date = datetime.strptime(date_folder.name, '%Y-%m-%d')
                
                if folder_date < cutoff_date:
                    # Calculate size
                    folder_size = sum(
                        f.stat().st_size for f in date_folder.rglob('*') if f.is_file()
                    )
                    total_size += folder_size
                    
                    print(f"   {'[DRY RUN]' if dry_run else '[DELETE]'} {date_folder.name} "
                          f"({folder_size / (1024*1024):.2f} MB)")
                    
                    if not dry_run:
                        shutil.rmtree(date_folder)
                    
                    deleted_count += 1
            
            except ValueError:
                # Skip invalid date folders
                pass
        
        print(f"\n{'Would delete' if dry_run else 'Deleted'} {deleted_count} folder(s), "
              f"{total_size / (1024*1024):.2f} MB total")
        
        if dry_run and deleted_count > 0:
            print(f"\n💡 Run with dry_run=False to actually delete")
        
        return deleted_count
    
    def view_sessions(self, date_str):
        """View all sessions for a specific date
        
        Args:
            date_str: Date in YYYY-MM-DD format
        """
        sessions_dir = self.base_dir / date_str / 'sessions'
        if not sessions_dir.exists():
            print(f"❌ No sessions found for {date_str}")
            return []
        
        sessions = []
        for session_file in sessions_dir.glob('session_*.json'):
            with open(session_file) as f:
                session_data = json.load(f)
                sessions.append(session_data)
        
        return sorted(sessions, key=lambda x: x['start_time'])


def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage date-based logs')
    parser.add_argument('command', choices=['list', 'stats', 'archive', 'cleanup', 'sessions'],
                       help='Command to execute')
    parser.add_argument('--date', help='Specific date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=30, help='Days to keep for cleanup')
    parser.add_argument('--execute', action='store_true', help='Actually execute cleanup (not dry-run)')
    
    args = parser.parse_args()
    
    manager = LogManager()
    
    if args.command == 'list':
        print("📅 Available log dates:\n")
        for date in manager.list_log_dates():
            print(f"   {date}")
    
    elif args.command == 'stats':
        print("📊 Log Statistics:\n")
        stats = manager.get_log_stats(args.date)
        for date, info in stats.items():
            print(f"   {date}:")
            print(f"      Files: {info['file_count']}")
            print(f"      Size:  {info['total_size_mb']:.2f} MB")
            print()
    
    elif args.command == 'archive':
        if not args.date:
            print("❌ --date required for archive command")
            return
        manager.archive_logs(args.date)
    
    elif args.command == 'cleanup':
        manager.cleanup_old_logs(args.days, dry_run=not args.execute)
    
    elif args.command == 'sessions':
        if not args.date:
            print("❌ --date required for sessions command")
            return
        
        print(f"🔍 Sessions for {args.date}:\n")
        sessions = manager.view_sessions(args.date)
        for session in sessions:
            print(f"   Session: {session['session_id']}")
            print(f"   Started: {session['start_time']}")
            print()


if __name__ == "__main__":
    # If run without arguments, show interactive menu
    import sys
    if len(sys.argv) == 1:
        print("=" * 70)
        print("📁 Log Management Utilities")
        print("=" * 70)
        
        manager = LogManager()
        
        print("\n📅 Recent Log Dates:")
        dates = manager.list_log_dates()[:10]
        for i, date in enumerate(dates, 1):
            print(f"   {i}. {date}")
        
        print("\n📊 Today's Log Stats:")
        today = datetime.now().strftime('%Y-%m-%d')
        stats = manager.get_log_stats(today)
        if today in stats:
            print(f"   Files: {stats[today]['file_count']}")
            print(f"   Size:  {stats[today]['total_size_mb']:.2f} MB")
        else:
            print("   No logs yet for today")
        
        print("\n💡 Usage:")
        print("   python manage_logs.py list           - List all log dates")
        print("   python manage_logs.py stats          - Show stats for all dates")
        print("   python manage_logs.py stats --date 2025-12-20  - Stats for specific date")
        print("   python manage_logs.py archive --date 2025-11-01  - Archive specific date")
        print("   python manage_logs.py cleanup --days 30  - Preview cleanup (dry-run)")
        print("   python manage_logs.py cleanup --days 30 --execute  - Actually delete old logs")
        print("   python manage_logs.py sessions --date 2025-12-20  - View sessions")
        print("=" * 70)
    else:
        main()
