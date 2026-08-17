"""
Update System API Routes

Endpoints for checking, downloading, and installing updates
"""

from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)

# Create blueprint
update_bp = Blueprint('updates', __name__, url_prefix='/api/updates')

# Will be injected by main app
updater = None

def init_update_routes(app, updater_instance):
    """Initialize update routes with updater instance"""
    global updater
    updater = updater_instance
    app.register_blueprint(update_bp)
    logger.info("✅ Update routes registered")


@update_bp.route('/check', methods=['GET'])
def check_for_updates():
    """Check if updates are available"""
    try:
        if not updater:
            return jsonify({
                "success": False,
                "error": "Updater not initialized"
            }), 500
        
        update_available, version = updater.check_for_updates()
        
        return jsonify({
            "success": True,
            "update_available": update_available,
            "current_version": str(updater.current_version),
            "latest_version": version,
            "release_notes": updater.release_notes if update_available else None,
            "download_url": updater.download_url if update_available else None
        })
    
    except Exception as e:
        logger.error(f"Update check failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@update_bp.route('/info', methods=['GET'])
def get_update_info():
    """Get current update status and configuration"""
    try:
        if not updater:
            return jsonify({
                "success": False,
                "error": "Updater not initialized"
            }), 500
        
        return jsonify({
            "success": True,
            **updater.get_update_info()
        })
    
    except Exception as e:
        logger.error(f"Failed to get update info: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@update_bp.route('/download', methods=['POST'])
def download_update():
    """Download available update"""
    try:
        if not updater:
            return jsonify({
                "success": False,
                "error": "Updater not initialized"
            }), 500
        
        if not updater.update_available:
            return jsonify({
                "success": False,
                "error": "No update available"
            }), 400
        
        # Download update
        update_file = updater.download_update()
        
        if update_file:
            return jsonify({
                "success": True,
                "message": "Update downloaded successfully",
                "file": str(update_file)
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to download update"
            }), 500
    
    except Exception as e:
        logger.error(f"Update download failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@update_bp.route('/install', methods=['POST'])
def install_update():
    """Install downloaded update"""
    try:
        if not updater:
            return jsonify({
                "success": False,
                "error": "Updater not initialized"
            }), 500
        
        data = request.get_json() or {}
        update_file = data.get('update_file')
        
        if not update_file:
            # Find latest downloaded update
            updates = list(updater.update_dir.glob("update-*.zip"))
            if not updates:
                return jsonify({
                    "success": False,
                    "error": "No update file found"
                }), 400
            update_file = max(updates, key=lambda p: p.stat().st_mtime)
        else:
            from pathlib import Path
            update_file = Path(update_file)
        
        # Install update
        success = updater.install_update(update_file)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Update installed! Please restart the application.",
                "requires_restart": True
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to install update"
            }), 500
    
    except Exception as e:
        logger.error(f"Update installation failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@update_bp.route('/config', methods=['GET', 'POST'])
def update_config():
    """Get or update configuration"""
    try:
        if not updater:
            return jsonify({
                "success": False,
                "error": "Updater not initialized"
            }), 500
        
        if request.method == 'GET':
            return jsonify({
                "success": True,
                "config": updater.config
            })
        
        # POST - update config
        data = request.get_json()
        
        if "auto_check" in data:
            updater.config["auto_check"] = bool(data["auto_check"])
        if "auto_download" in data:
            updater.config["auto_download"] = bool(data["auto_download"])
        if "auto_install" in data:
            updater.config["auto_install"] = bool(data["auto_install"])
        if "check_interval_hours" in data:
            updater.config["check_interval_hours"] = int(data["check_interval_hours"])
        
        updater._save_config()
        
        return jsonify({
            "success": True,
            "message": "Configuration updated",
            "config": updater.config
        })
    
    except Exception as e:
        logger.error(f"Config update failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@update_bp.route('/ignore/<version>', methods=['POST'])
def ignore_version(version):
    """Ignore a specific version"""
    try:
        if not updater:
            return jsonify({
                "success": False,
                "error": "Updater not initialized"
            }), 500
        
        updater.ignore_version(version)
        
        return jsonify({
            "success": True,
            "message": f"Version {version} will be ignored"
        })
    
    except Exception as e:
        logger.error(f"Failed to ignore version: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
