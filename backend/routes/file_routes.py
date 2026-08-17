from flask import Blueprint, jsonify, request, send_from_directory, render_template, Response, stream_with_context
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request
import os, json, sys, time, datetime
try:
    from backend.modern_web_backend import logger, api_logger, get_current_context
except ImportError:
    pass
    

file_bp = Blueprint('file', __name__)


try:
    from backend.modern_web_backend import *
except ImportError:
    from modern_web_backend import *
@file_bp.route('/api/files/organize', methods=['POST'])
@jwt_required()
def api_organize_files():
    """Organize files by type in a directory"""
    try:
        from ai_assistant.utils.file_ops import organize_files_by_type
        
        data = request.get_json()
        directory = data.get('directory')
        create_subfolders = data.get('create_subfolders', True)
        
        if not directory:
            return jsonify({"success": False, "error": "Directory path required"}), 400
        
        # Security: Basic path validation
        if not os.path.exists(directory):
            return jsonify({"success": False, "error": "Directory not found"}), 404
        
        result = organize_files_by_type(directory, create_subfolders)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"File organization error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@file_bp.route('/api/files/find-duplicates', methods=['POST'])
@jwt_required()
def api_find_duplicates():
    """Find duplicate files in a directory"""
    try:
        from ai_assistant.utils.file_ops import find_duplicate_files
        
        data = request.get_json()
        directory = data.get('directory')
        include_subdirs = data.get('include_subdirs', True)
        
        if not directory:
            return jsonify({"success": False, "error": "Directory path required"}), 400
        
        result = find_duplicate_files(directory, include_subdirs)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Duplicate file detection error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@file_bp.route('/api/files/search', methods=['POST'])
@jwt_required()
def api_search_files():
    """Search for files with advanced filtering"""
    try:
        from ai_assistant.utils.file_ops import smart_file_search
        
        data = request.get_json()
        directory = data.get('directory')
        pattern = data.get('pattern')
        search_content = data.get('search_content', False)
        file_types = data.get('file_types')
        
        if not directory or not pattern:
            return jsonify({"success": False, "error": "Directory and pattern required"}), 400
        
        result = smart_file_search(directory, pattern, search_content, file_types)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"File search error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@file_bp.route('/api/files/batch-rename', methods=['POST'])
@jwt_required()
def api_batch_rename():
    """Batch rename files using patterns"""
    try:
        from ai_assistant.utils.file_ops import batch_rename_files
        
        data = request.get_json()
        directory = data.get('directory')
        pattern = data.get('pattern')
        replacement = data.get('replacement')
        preview = data.get('preview', True)
        
        if not all([directory, pattern, replacement]):
            return jsonify({"success": False, "error": "Directory, pattern, and replacement required"}), 400
        
        result = batch_rename_files(directory, pattern, replacement, preview)
        
        return jsonify({
            "success": True,
            "result": result,
            "preview": preview,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Batch rename error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@file_bp.route('/api/files/analyze-directory', methods=['POST'])
@jwt_required()
def api_analyze_directory():
    """Analyze directory structure and contents"""
    try:
        from ai_assistant.utils.file_ops import analyze_directory_structure
        
        data = request.get_json()
        directory = data.get('directory')
        max_depth = data.get('max_depth', 3)
        
        if not directory:
            return jsonify({"success": False, "error": "Directory path required"}), 400
        
        result = analyze_directory_structure(directory, max_depth)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Directory analysis error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@file_bp.route('/api/ocr/check-dependencies', methods=['GET'])
def api_ocr_check_dependencies():
    """Check OCR dependencies status"""
    try:
        from ai_assistant.vision.document_ocr import check_ocr_dependencies
        
        result = check_ocr_dependencies()
        
        return jsonify({
            "success": True,
            "dependencies_status": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"OCR dependency check error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@file_bp.route('/api/ocr/extract-image', methods=['POST'])
@jwt_required()
def api_extract_text_image():
    """Extract text from image using OCR"""
    try:
        from ai_assistant.vision.document_ocr import extract_text_from_image
        
        data = request.get_json()
        image_path = data.get('image_path')
        language = data.get('language', 'eng')
        enhance = data.get('enhance', True)
        
        if not image_path:
            return jsonify({"success": False, "error": "Image path required"}), 400
        
        result = extract_text_from_image(image_path, language, enhance)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Image OCR error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@file_bp.route('/api/ocr/extract-pdf', methods=['POST'])
@jwt_required()
def api_extract_text_pdf():
    """Extract text from PDF document"""
    try:
        from ai_assistant.vision.document_ocr import extract_text_from_pdf
        
        data = request.get_json()
        pdf_path = data.get('pdf_path')
        page_range = data.get('page_range')
        
        if not pdf_path:
            return jsonify({"success": False, "error": "PDF path required"}), 400
        
        result = extract_text_from_pdf(pdf_path, page_range)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@file_bp.route('/api/ocr/analyze-document', methods=['POST'])
@jwt_required()
def api_analyze_document():
    """Analyze document structure and metadata"""
    try:
        from ai_assistant.vision.document_ocr import analyze_document_structure
        
        data = request.get_json()
        file_path = data.get('file_path')
        
        if not file_path:
            return jsonify({"success": False, "error": "File path required"}), 400
        
        result = analyze_document_structure(file_path)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Document analysis error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@file_bp.route('/api/ocr/extract-info', methods=['POST'])
@jwt_required()
def api_extract_key_information():
    """Extract key information from text"""
    try:
        from ai_assistant.vision.document_ocr import extract_key_information
        
        data = request.get_json()
        text = data.get('text')
        info_type = data.get('info_type', 'general')
        
        if not text:
            return jsonify({"success": False, "error": "Text required"}), 400
        
        result = extract_key_information(text, info_type)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Information extraction error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500