#!/usr/bin/env python3
"""
Secure Email Manager - Address security vulnerabilities in email processing workflow.
Implements proper input validation, sanitization, and security controls.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("SecureEmailManager")

# Security configuration - use environment variables
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'your-secure-email@example.com')
ALLOWED_MODELS = ['gpt-4-turbo-preview', 'gpt-3.5-turbo', 'claude-3-opus']
MAX_EMAIL_SIZE = 50000  # 50KB
MAX_ATTACHMENTS = 10
MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024  # 5MB
RATE_LIMIT_WINDOW = 3600  # 1 hour
MAX_REQUESTS_PER_WINDOW = 10

# Rate limiting storage (in production, use Redis or similar)
request_log = {}

# Email processing database path
DB_PATH = os.path.join(
    os.path.dirname(__file__), 
    'skills', 'smart-email', 'data', 'email_secure.db'
)

class SecurityError(Exception):
    """Security validation errors"""
    pass

class EmailValidator:
    """Email validation and sanitization"""
    
    @staticmethod
    def validate_email_size(email_data: Dict) -> None:
        """Validate email size to prevent DoS"""
        if email_data.get('body', '').__len__() > MAX_EMAIL_SIZE:
            raise SecurityError(f"Email too large: {email_data.get('body', '').__len__()} bytes > {MAX_EMAIL_SIZE}")
    
    @staticmethod
    def validate_attachments(attachments: List[Dict]) -> None:
        """Validate attachment count and size"""
        if len(attachments) > MAX_ATTACHMENTS:
            raise SecurityError(f"Too many attachments: {len(attachments)} > {MAX_ATTACHMENTS}")
        
        for i, attachment in enumerate(attachments):
            if attachment.get('size', 0) > MAX_ATTACHMENT_SIZE:
                raise SecurityError(f"Attachment {i} too large: {attachment.get('size')} > {MAX_ATTACHMENT_SIZE}")
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize input to prevent injection attacks"""
        if not text:
            return text
        
        # Remove HTML/JS tags
        sanitized = re.sub(r'<[^>]*>', '', text)
        
        # Remove potential script content
        sanitized = re.sub(r'script', '', sanitized, flags=re.IGNORECASE)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Limit length
        if len(sanitized) > 5000:
            sanitized = sanitized[:5000]
        
        return sanitized
    
    @staticmethod
    def validate_sender(sender: str) -> bool:
        """Basic sender validation"""
        if not sender or '@' not in sender:
            return False
        
        # Remove potential malicious patterns
        if any(pattern in sender.lower() for pattern in ['@example', '@test', '@fake', '@temp']):
            return False
        
        return True
class RateLimiter:
    """Simple rate limiting implementation"""
    
    @staticmethod
    def is_allowed(client_id: str) -> bool:
        """Check if client is within rate limits"""
        current_time = datetime.now().timestamp()
        
        if client_id not in request_log:
            request_log[client_id] = []
        
        # Remove old requests
        request_log[client_id] = [
            req_time for req_time in request_log[client_id]
            if current_time - req_time < RATE_LIMIT_WINDOW
        ]
        
        if len(request_log[client_id]) >= MAX_REQUESTS_PER_WINDOW:
            logger.warning(f"Rate limit exceeded for client {client_id}")
            return False
        
        # Add current request
        request_log[client_id].append(current_time)
        return True
class SecureEmailProcessor:
    """Main email processing class with security controls"""
    
    def __init__(self):
        self.validator = EmailValidator()
        self.rate_limiter = RateLimiter()
        self._ensure_database()
    
    def _ensure_database(self) -> None:
        """Ensure secure database exists"""
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Processed emails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_emails (
                email_uid TEXT PRIMARY KEY,
                sender TEXT,
                subject TEXT,
                category TEXT,
                priority TEXT,
                summary TEXT,
                delete_flag INTEGER,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                security_flags TEXT
            )
        """)
        
        # Audit logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                email_uid TEXT,
                action TEXT,
                decision TEXT,
                ip_address TEXT,
                user_agent TEXT,
                security_flags TEXT
            )
        """)
        
        # Quarantine table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quarantined_emails (
                email_uid TEXT PRIMARY KEY,
                sender TEXT,
                subject TEXT,
                reason TEXT,
                quarantined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_action(self, email_uid: str, action: str, decision: str, 
                   security_flags: Dict = None) -> None:
        """Log security-relevant actions"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO audit_logs (email_uid, action, decision, security_flags) VALUES (?, ?, ?, ?)",
                (email_uid, action, decision, json.dumps(security_flags or {}))
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"AUDIT: {action} for email {email_uid} - {decision}")
            
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
    
    def process_email(self, email_data: Dict, client_id: str = "default") -> Dict:
        """Process email with security controls"""
        
        # Rate limiting
        if not self.rate_limiter.is_allowed(client_id):
            self.log_action(
                email_data.get('uid', 'unknown'),
                'rate_limit_reject',
                'client exceeded rate limits'
            )
            raise SecurityError("Rate limit exceeded. Please try again later.")
        
        email_uid = email_data.get('uid')
        
        try:
            # Security flags for tracking
            security_flags = {
                'validated': True,
                'sanitized': False,
                'deleted': False,
                'draft_created': False
            }
            
            # 1. Input validation
            logger.info(f"Processing email: {email_uid} from {email_data.get('sender', 'unknown')}")
            
            # Validate email size
            self.validator.validate_email_size(email_data)
            
            # Validate attachments
            attachments = email_data.get('attachments', [])
            self.validator.validate_attachments(attachments)
            
            # 2. Sanitize input
            sanitized_subject = self.validator.sanitize_input(email_data.get('subject', ''))
            sanitized_body = self.validator.sanitize_input(email_data.get('body', ''))
            
            security_flags['sanitized'] = True
            
            # 3. Model validation (if applicable)
            # In a real implementation, validate the AI model being used
            
            # 4. Basic classification logic
            result = self._classify_email(sanitized_subject, sanitized_body)
            
            # 5. Log processing decision
            self.log_action(email_uid, 'process_email', 'success', security_flags)
            
            return {
                'email_uid': email_uid,
                'status': 'processed',
                'classification': result,
                'security_flags': security_flags
            }
            
        except SecurityError as e:
            # Security violation - quarantine email
            self._quarantine_email(email_data, str(e))
            self.log_action(
                email_uid,
                'security_violation',
                f'quarantined: {str(e)}'
            )
            
            raise
            
        except Exception as e:
            # Unexpected error - log and handle gracefully
            self.log_action(
                email_uid,
                'processing_error',
                f'error: {str(e)}'
            )
            
            logger.error(f"Error processing email {email_uid}: {e}")
            raise
    
    def _classify_email(self, subject: str, body: str) -> Dict:
        """Classify email based on content"""
        
        # Rule-based classification
        result = {
            'category': 'General',
            'priority': 'Medium',
            'summary': subject[:100] + '...' if len(subject) > 100 else subject,
            'draft_reply': None,
            'delete': False
        }
        
        # Career-related emails
        if any(keyword in subject.lower() for keyword in ['job', 'career', 'apply', 'developer']):
            result.update({
                'category': 'Careers',
                'priority': 'High',
                'draft_reply': f"Thank you for contacting me regarding the '{subject[:50]}' opportunity. I am highly interested and would love to review the next steps. Best regards, {ADMIN_EMAIL}."
            })
        
        # Technology/Specialized content
        elif any(keyword in body.lower() for keyword in ['google', 'cloud', 'ai', 'machine learning']):
            result.update({
                'category': 'Technology',
                'priority': 'Medium',
                'draft_reply': f"Hi {result.get('sender', 'Team')}, thank you for the update on {subject}. I look forward to experimenting with this! Best, {ADMIN_EMAIL}."
            })
        
        # Marketing/Newsletter detection
        elif any(keyword in subject.lower() for keyword in ['newsletter', 'marketing', 'promotion']):
            result['delete'] = True
            logger.info(f"Marked as marketing email: {subject}")
        
        return result
    
    def _quarantine_email(self, email_data: Dict, reason: str) -> None:
        """Quarantine security-violating emails"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO quarantined_emails (email_uid, sender, subject, reason) VALUES (?, ?, ?, ?)",
                (
                    email_data.get('uid'),
                    email_data.get('sender'),
                    email_data.get('subject', '')[:200],
                    reason
                )
            )
            
            conn.commit()
            conn.close()
            
            logger.warning(f"QUARANTINED email {email_data.get('uid')}: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to quarantine email: {e}")
    
    def get_statistics(self) -> Dict:
        """Get processing statistics"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Total processed emails
            cursor.execute("SELECT COUNT(*) FROM processed_emails")
            total = cursor.fetchone()[0]
            
            # Recent activity
            cursor.execute("""
                SELECT COUNT(*) FROM audit_logs 
                WHERE timestamp > datetime('now', '-24 hours')
            """)
            recent = cursor.fetchone()[0]
            
            # Quarantine count
            cursor.execute("SELECT COUNT(*) FROM quarantined_emails")
            quarantined = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_processed': total,
                'recent_activity': recent,
                'quarantined': quarantined,
                'security_flags': 'implemented'
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {'error': str(e)}
class MockGmailService:
    """Mock Gmail service for testing (replace with real IMAP implementation)"""
    
    def __init__(self):
        self.processor = SecureEmailProcessor()
    
    def fetch_unread_emails(self) -> List[Dict]:
        """Fetch unread emails (mock implementation)"""
        # This would be replaced with actual IMAP code
        mock_emails = [
            {
                'uid': 'email_001',
                'sender': 'client@example.com',
                'subject': 'Job Opportunity - Senior Developer Position',
                'body': 'We have a senior developer position available...',
                'attachments': []
            },
            {
                'uid': 'email_002', 
                'sender': 'newsletter@spam.com',
                'subject': 'Weekly Tech Newsletter - Very Important!',
                'body': 'This is another promotional email...',
                'attachments': [{'name': 'ad.pdf', 'size': 1024}]
            }
        ]
        
        processed_emails = []
        
        for email in mock_emails:
            try:
                result = self.processor.process_email(email)
                processed_emails.append({
                    'email': email,
                    'result': result
                })
                
                # Auto-draft reply for valid emails
                if result['classification']['draft_reply'] and not result['classification']['delete']:
                    logger.info(f"Draft reply created for email {email['uid']}")
                    
            except SecurityError as e:
                logger.warning(f"Email {email['uid']} rejected: {e}")
                continue
        
        return processed_emails
    
    def save_draft_locally(self, email: Dict, draft_content: str) -> None:
        """Save draft locally (in production, use proper email service)"""
        logger.info(f"Saving draft for email: {email.get('subject', 'No subject')}")
        logger.info(f"Draft content: {draft_content[:100]}...")
        
        # In production: use email service API to save drafts
        # For now: log the action
        
    def move_to_trash(self, email: Dict) -> None:
        """Mark email for deletion"""
        logger.info(f"Moving email to trash: {email.get('subject', 'No subject')}")
        # In production: use IMAP to move to trash
        # For now: log the action
class EmailManager:
    """Main email manager with secure defaults"""
    
    def __init__(self):
        self.gmail = MockGmailService()
        self.processor = SecureEmailProcessor()
    
    def process_all_emails(self) -> Dict:
        """Process all unread emails with security controls"""
        logger.info("=" * 60)
        logger.info("Secure Email Manager Started")
        logger.info("=" * 60)
        
        try:
            # Fetch emails
            emails_result = self.gmail.fetch_unread_emails()
            logger.info(f"Fetched {len(emails_result)} emails for processing")
            
            # Generate statistics
            stats = self.processor.get_statistics()
            
            logger.info(f"Statistics: {stats}")
            logger.info("=" * 60)
            logger.info("Secure Email Manager Completed Successfully")
            logger.info("=" * 60)
            
            return {
                'status': 'completed',
                'emails_processed': len(emails_result),
                'statistics': stats,
                'security': 'implemented'
            }
            
        except Exception as e:
            logger.error(f"Email Manager failed: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'security': 'basic_protection'
            }
def main():
    """Entry point for the secure email manager"""
    print("🔒 Secure Email Manager - Security Hardened Version")
    print("=" * 60)
    
    # Initialize with secure defaults
    email_manager = EmailManager()
    
    # Process emails
    result = email_manager.process_all_emails()
    
    print(f"\nResult: {result}")
    print("\n✅ Security features implemented:")
    print("  • Input validation and sanitization")
    print("  • Rate limiting (10 requests/hour)")
    print("  • Email size/attachment limits")
    print("  • Audit logging")
    print("  • Error handling with quarantine")
    print("  • Environment-based configuration")
    print("  • Secure email processing")
    
    return result
if __name__ == "__main__":
    main()