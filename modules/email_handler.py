# Email Management Module
"""
Gmail integration and email management functions for the YourDaddy AI Assistant.

Provides:
- OAuth2 authentication with Gmail API
- Read, send, search, and manage emails
- Quick reply templates
- Email organization and filtering
"""

import os
import datetime
import pickle
import base64
import email
import re
from pathlib import Path
from typing import List, Dict, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API scope for full access
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify'
]


class GmailManager:
    """
    Manages Gmail API authentication and operations
    """
    
    _instance = None  # Singleton instance
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GmailManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.service = None
        self.credentials_path = Path('credentials.json')
        self.token_path = Path('gmail_token.pickle')
        self._initialized = True
    
    def setup_auth(self) -> str:
        """
        Sets up Gmail API authentication
        Returns status message
        """
        try:
            creds = None
            
            # Load existing credentials
            if self.token_path.exists():
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception:
                        # Token refresh failed, need to re-authenticate
                        creds = None
                
                if not creds:
                    if not self.credentials_path.exists():
                        return self._get_setup_instructions()
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(self.credentials_path), SCOPES)
                        creds = flow.run_local_server(port=0)
                    except Exception as e:
                        return f"❌ Authentication failed: {str(e)}"
                
                # Save credentials for next run
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            # Build the service
            self.service = build('gmail', 'v1', credentials=creds)
            
            # Test the service by getting user profile
            profile = self.service.users().getProfile(userId='me').execute()
            email_address = profile.get('emailAddress', 'Unknown')
            
            return f"✅ Gmail authenticated successfully!\n📧 Connected to: {email_address}"
        
        except HttpError as e:
            return f"❌ Gmail API error: {str(e)}"
        except Exception as e:
            return f"❌ Gmail authentication error: {str(e)}"
    
    def _get_setup_instructions(self) -> str:
        """Returns setup instructions for Gmail API"""
        return """❌ Gmail not configured: 'credentials.json' not found.

🔧 Setup Instructions:

1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Create a new project or select an existing one
3. Enable Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as application type
   - Give it a name (e.g., "YourDaddy Assistant")
5. Download the credentials:
   - Click the download button (⬇️) next to your OAuth client
   - Save as 'credentials.json' in the project root folder
6. Run the setup again

Note: You'll need to add yourself as a test user if your app is in testing mode.
You can reuse the same credentials.json from Google Calendar setup.
"""
    
    def get_service(self):
        """
        Get authenticated Gmail service, initialize if needed
        """
        if self.service is None:
            result = self.setup_auth()
            if "❌" in result:
                return None
        return self.service
    
    def is_authenticated(self) -> bool:
        """Check if Gmail is authenticated"""
        if self.service is None:
            service = self.get_service()
            return service is not None
        return True


def setup_email_auth() -> str:
    """
    Sets up Gmail API authentication. Returns status message.
    User needs to run this once to authenticate.
    """
    print("--- 'Hands' (setup_email_auth) activated ---")
    manager = GmailManager()
    return manager.setup_auth()


def get_gmail_service():
    """Helper function to get authenticated Gmail service."""
    manager = GmailManager()
    return manager.get_service()


def get_inbox_summary(max_emails: int = 10) -> str:
    """
    Gets a summary of recent emails in the inbox.
    :param max_emails: Maximum number of emails to retrieve (default 10)
    """
    print(f"--- 'Hands' (get_inbox_summary) activated. Max emails: {max_emails} ---")
    try:
        service = get_gmail_service()
        if not service:
            return "❌ Gmail not authenticated. Please run 'setup email authentication' first."
        
        # Validate input
        max_emails = max(1, min(50, max_emails))
        
        # Get list of messages
        results = service.users().messages().list(
            userId='me', 
            labelIds=['INBOX'], 
            maxResults=max_emails
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return "📭 Your inbox is empty!"
        
        inbox_report = f"📬 INBOX SUMMARY ({len(messages)} recent emails)\n"
        inbox_report += "━" * 80 + "\n"
        
        for message in messages[:max_emails]:
            # Get message details
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload'].get('headers', [])
            
            # Extract relevant information
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            
            # Parse date
            try:
                parsed_date = email.utils.parsedate_to_datetime(date)
                formatted_date = parsed_date.strftime("%m/%d %I:%M %p")
            except:
                formatted_date = date[:10]
            
            # Extract sender email and name
            sender_clean = extract_email_address(sender)
            sender_name = extract_display_name(sender)
            
            # Check if unread
            labels = msg.get('labelIds', [])
            unread_indicator = "🆕" if 'UNREAD' in labels else "📧"
            
            inbox_report += f"{unread_indicator} [{formatted_date}] **{sender_name}**\n"
            inbox_report += f"   📄 {subject[:60]}{'...' if len(subject) > 60 else ''}\n\n"
        
        return inbox_report
        
    except HttpError as e:
        return f"❌ Gmail API error: {str(e)}"
    except Exception as e:
        return f"❌ Error getting inbox summary: {str(e)}"

def send_email(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> str:
    """
    Sends an email using Gmail API.
    :param to: Recipient email address
    :param subject: Email subject
    :param body: Email body content
    :param cc: CC recipients (optional)
    :param bcc: BCC recipients (optional)
    """
    print(f"--- 'Hands' (send_email) activated. To: {to}, Subject: {subject} ---")
    try:
        service = get_gmail_service()
        if not service:
            return "❌ Gmail not authenticated. Please run 'setup email authentication' first."
        
        # Validate email address
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', to):
            return f"❌ Invalid recipient email address: {to}"
        
        # Create message
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        if cc:
            message['cc'] = cc
        if bcc:
            message['bcc'] = bcc
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send email
        send_message = service.users().messages().send(
            userId='me', body={'raw': raw_message}).execute()
        
        return f"✅ Email sent successfully to {to}!\nMessage ID: {send_message['id']}"
        
    except HttpError as e:
        return f"❌ Gmail API error: {str(e)}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"

def search_emails(query: str, max_results: int = 10) -> str:
    """
    Searches emails using Gmail search syntax.
    :param query: Search query (e.g., "from:someone@example.com", "subject:meeting")
    :param max_results: Maximum number of results to return
    """
    print(f"--- 'Hands' (search_emails) activated. Query: {query} ---")
    try:
        service = get_gmail_service()
        if not service:
            return "❌ Gmail not authenticated. Please run 'setup email authentication' first."
        
        # Validate input
        max_results = max(1, min(50, max_results))
        
        # Search for messages
        results = service.users().messages().list(
            userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return f"🔍 No emails found matching '{query}'"
        
        search_report = f"🔍 EMAIL SEARCH RESULTS for '{query}' ({len(messages)} found)\n"
        search_report += "━" * 80 + "\n"
        
        for message in messages:
            # Get message details
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload'].get('headers', [])
            
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            
            # Parse date
            try:
                parsed_date = email.utils.parsedate_to_datetime(date)
                formatted_date = parsed_date.strftime("%m/%d/%Y %I:%M %p")
            except:
                formatted_date = date[:16]
            
            sender_name = extract_display_name(sender)
            
            search_report += f"📧 [{formatted_date}] {sender_name}\n   📄 {subject}\n\n"
        
        return search_report
        
    except HttpError as e:
        return f"❌ Gmail API error: {str(e)}"
    except Exception as e:
        return f"❌ Error searching emails: {str(e)}"

def read_email_content(email_id: str = "", sender: str = "", subject_contains: str = "") -> str:
    """
    Reads the full content of a specific email.
    :param email_id: Specific Gmail message ID
    :param sender: Filter by sender email/name
    :param subject_contains: Filter by subject containing text
    """
    print(f"--- 'Hands' (read_email_content) activated ---")
    try:
        service = get_gmail_service()
        if not service:
            return "❌ Gmail not authenticated. Please use 'setup email authentication' first."
        
        # If specific ID provided, use it
        if email_id:
            target_id = email_id
        else:
            # Search for email based on criteria
            query_parts = []
            if sender:
                query_parts.append(f"from:{sender}")
            if subject_contains:
                query_parts.append(f"subject:{subject_contains}")
            
            if not query_parts:
                return "❌ Please provide either email_id, sender, or subject_contains parameter."
            
            query = " ".join(query_parts)
            results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()
            messages = results.get('messages', [])
            
            if not messages:
                return f"❌ No email found matching the criteria."
            
            target_id = messages[0]['id']
        
        # Get full message content
        message = service.users().messages().get(userId='me', id=target_id, format='full').execute()
        headers = message['payload'].get('headers', [])
        
        # Extract headers
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
        to = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown')
        
        # Extract body
        body = extract_email_body(message['payload'])
        
        # Format date
        try:
            parsed_date = email.utils.parsedate_to_datetime(date)
            formatted_date = parsed_date.strftime("%A, %B %d, %Y at %I:%M %p")
        except:
            formatted_date = date
        
        email_content = f"""📧 EMAIL CONTENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 From: {extract_display_name(sender)} <{extract_email_address(sender)}>
📥 To: {to}
📅 Date: {formatted_date}
📄 Subject: {subject}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{body}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return email_content
        
    except Exception as e:
        return f"Error reading email content: {e}"

def get_unread_count() -> str:
    """
    Gets the count of unread emails in inbox.
    """
    print("--- 'Hands' (get_unread_count) activated ---")
    try:
        service = get_gmail_service()
        if not service:
            return "❌ Gmail not authenticated. Please use 'setup email authentication' first."
        
        # Get unread messages
        results = service.users().messages().list(
            userId='me', labelIds=['INBOX', 'UNREAD']).execute()
        messages = results.get('messages', [])
        
        count = len(messages)
        
        if count == 0:
            return "✅ No unread emails! Your inbox is all caught up."
        elif count == 1:
            return "📬 You have 1 unread email."
        else:
            return f"📬 You have {count} unread emails."
            
    except Exception as e:
        return f"Error getting unread count: {e}"

def mark_email_read(email_id: str = "", sender: str = "", subject_contains: str = "") -> str:
    """
    Marks an email as read.
    :param email_id: Specific Gmail message ID
    :param sender: Filter by sender email/name  
    :param subject_contains: Filter by subject containing text
    """
    print(f"--- 'Hands' (mark_email_read) activated ---")
    try:
        service = get_gmail_service()
        if not service:
            return "❌ Gmail not authenticated. Please use 'setup email authentication' first."
        
        # Find email ID if not provided
        if not email_id:
            query_parts = []
            if sender:
                query_parts.append(f"from:{sender}")
            if subject_contains:
                query_parts.append(f"subject:{subject_contains}")
            
            if not query_parts:
                return "❌ Please provide either email_id, sender, or subject_contains parameter."
            
            query = " ".join(query_parts)
            results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()
            messages = results.get('messages', [])
            
            if not messages:
                return "❌ No email found matching the criteria."
            
            email_id = messages[0]['id']
        
        # Remove UNREAD label
        service.users().messages().modify(
            userId='me', id=email_id, 
            body={'removeLabelIds': ['UNREAD']}).execute()
        
        return f"✅ Email marked as read! ID: {email_id}"
        
    except Exception as e:
        return f"Error marking email as read: {e}"

def delete_email(email_id: str = "", sender: str = "", subject_contains: str = "") -> str:
    """
    Deletes an email (moves to trash).
    :param email_id: Specific Gmail message ID
    :param sender: Filter by sender email/name
    :param subject_contains: Filter by subject containing text
    """
    print(f"--- 'Hands' (delete_email) activated ---")
    try:
        service = get_gmail_service()
        if not service:
            return "❌ Gmail not authenticated. Please use 'setup email authentication' first."
        
        # Find email ID if not provided
        if not email_id:
            query_parts = []
            if sender:
                query_parts.append(f"from:{sender}")
            if subject_contains:
                query_parts.append(f"subject:{subject_contains}")
            
            if not query_parts:
                return "❌ Please provide either email_id, sender, or subject_contains parameter."
            
            query = " ".join(query_parts)
            results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()
            messages = results.get('messages', [])
            
            if not messages:
                return "❌ No email found matching the criteria."
            
            email_id = messages[0]['id']
        
        # Move to trash
        service.users().messages().trash(userId='me', id=email_id).execute()
        
        return f"🗑️ Email moved to trash! ID: {email_id}"
        
    except Exception as e:
        return f"Error deleting email: {e}"

def compose_quick_reply(to: str, reply_type: str = "acknowledge", custom_message: str = "") -> str:
    """
    Sends a quick reply with predefined templates.
    :param to: Recipient email address
    :param reply_type: Type of reply (acknowledge, thanks, meeting_accept, meeting_decline, follow_up)
    :param custom_message: Custom message to append (optional)
    """
    print(f"--- 'Hands' (compose_quick_reply) activated. Type: {reply_type} ---")
    
    templates = {
        "acknowledge": {
            "subject": "Re: Acknowledgment",
            "body": "Thank you for your email. I have received it and will review the details.\\n\\nBest regards"
        },
        "thanks": {
            "subject": "Re: Thank you",
            "body": "Thank you very much for your assistance. I really appreciate your help.\\n\\nBest regards"
        },
        "meeting_accept": {
            "subject": "Re: Meeting Acceptance",
            "body": "Thank you for the meeting invitation. I confirm my attendance and look forward to our discussion.\\n\\nBest regards"
        },
        "meeting_decline": {
            "subject": "Re: Meeting Decline",
            "body": "Thank you for the meeting invitation. Unfortunately, I won't be able to attend due to a scheduling conflict.\\n\\nBest regards"
        },
        "follow_up": {
            "subject": "Re: Follow-up",
            "body": "I wanted to follow up on our previous discussion. Please let me know if you need any additional information.\\n\\nBest regards"
        }
    }
    
    if reply_type not in templates:
        return f"❌ Unknown reply type: {reply_type}. Available types: {', '.join(templates.keys())}"
    
    template = templates[reply_type]
    body = template["body"]
    
    if custom_message:
        body += f"\\n\\n{custom_message}"
    
    return send_email(to, template["subject"], body)

# Helper functions
def extract_email_address(email_string: str) -> str:
    """Extracts email address from 'Name <email@domain.com>' format."""
    match = re.search(r'<(.+?)>', email_string)
    if match:
        return match.group(1)
    return email_string.strip()

def extract_display_name(email_string: str) -> str:
    """Extracts display name from 'Name <email@domain.com>' format."""
    if '<' in email_string:
        name = email_string.split('<')[0].strip().strip('"')
        return name if name else extract_email_address(email_string)
    return email_string

def extract_email_body(payload) -> str:
    """Recursively extracts email body from Gmail API payload."""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            body += extract_email_body(part)
    else:
        if payload.get('body', {}).get('data'):
            if payload['mimeType'] == 'text/plain':
                data = payload['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif payload['mimeType'] == 'text/html':
                # For HTML, we might want to strip HTML tags (simplified)
                data = payload['body']['data']
                html_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                # Simple HTML tag removal (basic)
                body = re.sub(r'<[^>]+>', '', html_body)
    
    return body


# Export all functions
__all__ = [
    'GmailManager',
    'setup_email_auth',
    'get_gmail_service',
    'get_inbox_summary',
    'send_email',
    'search_emails',
    'read_email_content',
    'get_unread_count',
    'mark_email_read',
    'delete_email',
    'compose_quick_reply',
    'extract_email_address',
    'extract_display_name',
    'extract_email_body'
]