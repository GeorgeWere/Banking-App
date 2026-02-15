# utils/logger.py
import logging
import logging.handlers
import os
import traceback
import json
from datetime import datetime
import socket

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for SIEM-compatible logs"""
    
    def __init__(self):
        super().__init__()
        self.hostname = socket.gethostname()
    
    def format(self, record):
        log_record = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'hostname': self.hostname,
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add custom fields from 'extra' parameter
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'ip'):
            log_record['ip_address'] = record.ip
        if hasattr(record, 'action'):
            log_record['action'] = record.action
        if hasattr(record, 'details'):
            try:
                # Try to parse details as JSON
                if isinstance(record.details, str):
                    log_record['details'] = json.loads(record.details)
                else:
                    log_record['details'] = record.details
            except:
                log_record['details'] = record.details
        
        return json.dumps(log_record)

class BankingLogger:
    """Centralized logging for banking application - SIEM Compatible"""
    
    def __init__(self):
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # JSON Formatter for all logs
        json_formatter = JSONFormatter()
        
        # 1. Application Log
        self.app_logger = logging.getLogger('application')
        self.app_logger.setLevel(logging.DEBUG)
        app_handler = logging.handlers.RotatingFileHandler(
            'logs/application.json', maxBytes=10485760, backupCount=5
        )
        app_handler.setFormatter(json_formatter)
        self.app_logger.addHandler(app_handler)
        
        # 2. Transaction Log
        self.txn_logger = logging.getLogger('transactions')
        self.txn_logger.setLevel(logging.INFO)
        txn_handler = logging.handlers.RotatingFileHandler(
            'logs/transactions.json', maxBytes=10485760, backupCount=5
        )
        txn_handler.setFormatter(json_formatter)
        self.txn_logger.addHandler(txn_handler)
        
        # 3. Audit Log
        self.audit_logger = logging.getLogger('audit')
        self.audit_logger.setLevel(logging.INFO)
        audit_handler = logging.handlers.RotatingFileHandler(
            'logs/audit.json', maxBytes=10485760, backupCount=5
        )
        audit_handler.setFormatter(json_formatter)
        self.audit_logger.addHandler(audit_handler)
        
        # 4. Error Log
        self.error_logger = logging.getLogger('errors')
        self.error_logger.setLevel(logging.ERROR)
        error_handler = logging.handlers.RotatingFileHandler(
            'logs/errors.json', maxBytes=10485760, backupCount=5
        )
        error_handler.setFormatter(json_formatter)
        self.error_logger.addHandler(error_handler)
        
        # 5. Performance Log
        self.perf_logger = logging.getLogger('performance')
        self.perf_logger.setLevel(logging.INFO)
        perf_handler = logging.handlers.RotatingFileHandler(
            'logs/performance.json', maxBytes=10485760, backupCount=5
        )
        perf_handler.setFormatter(json_formatter)
        self.perf_logger.addHandler(perf_handler)
    
    def log_app(self, level, message, **kwargs):
        """Log application event"""
        extra = {}
        extra.update(kwargs)
        getattr(self.app_logger, level)(message, extra=extra)
    
    def log_transaction(self, transaction_id, from_acc, to_acc, amount, status, user_id=None, **kwargs):
        """Log financial transaction"""
        extra = {
            'transaction_id': transaction_id,
            'from_account': from_acc,
            'to_account': to_acc,
            'amount': amount,
            'status': status,
            'user_id': user_id or 'system',
            'event_type': 'transaction'
        }
        extra.update(kwargs)
        self.txn_logger.info('Transaction', extra=extra)
    
    def log_audit(self, user_id, ip, action, details):
        """Log security audit event"""
        extra = {
            'user_id': user_id or 'anonymous',
            'ip_address': ip,
            'action': action,
            'details': details,
            'event_type': 'audit'
        }
        self.audit_logger.info('Audit Event', extra=extra)
    
    def log_error(self, error, **kwargs):
        """Log error with traceback"""
        extra = {
            'error': str(error),
            'error_type': type(error).__name__,
            'traceback': traceback.format_exc(),
            'event_type': 'error'
        }
        extra.update(kwargs)
        self.error_logger.error('Error occurred', extra=extra)
    
    def log_performance(self, endpoint, duration_ms, user_id=None):
        """Log performance metrics"""
        extra = {
            'endpoint': endpoint,
            'duration_ms': round(duration_ms, 2),
            'user_id': user_id or 'anonymous',
            'event_type': 'performance'
        }
        self.perf_logger.info('Performance Metric', extra=extra)

# Create global logger instance
bank_logger = BankingLogger()