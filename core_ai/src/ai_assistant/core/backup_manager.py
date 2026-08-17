import os
import shutil
from datetime import datetime
from pathlib import Path

class BackupManager:
    def __init__(self):
        self.src_dir = Path(__file__).parent.parent.parent.parent
        self.config_dir = self.src_dir / 'config'
        self.backup_dir = self.src_dir / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        
    def backup_settings(self):
        """Create a zip backup of the config directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"settings_backup_{timestamp}"
        
        try:
            if not self.config_dir.exists():
                print("❌ Config directory not found.")
                return False
                
            shutil.make_archive(
                str(self.backup_dir / backup_name),
                'zip',
                self.config_dir
            )
            print(f"✅ Settings successfully backed up to backups/{backup_name}.zip")
            return True
        except Exception as e:
            print(f"❌ Failed to backup settings: {e}")
            return False
            
    def list_backups(self):
        """List all available backups"""
        backups = list(self.backup_dir.glob("*.zip"))
        if not backups:
            print("No backups found.")
            return []
            
        print("Available Backups:")
        for idx, backup in enumerate(sorted(backups, reverse=True)):
            size_kb = backup.stat().st_size / 1024
            print(f"{idx + 1}. {backup.name} ({size_kb:.1f} KB)")
        return backups

if __name__ == "__main__":
    bm = BackupManager()
    print("Running BackupManager...")
    bm.backup_settings()
    bm.list_backups()
