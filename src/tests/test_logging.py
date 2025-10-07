"""
Unit tests voor logging module
"""

import unittest
import tempfile
import os
import logging
from pathlib import Path

from ..logging import setup_logging, get_logger, set_log_level, add_file_handler


class TestLogging(unittest.TestCase):
    
    def setUp(self):
        """Setup test fixtures"""
        # Create temporary log file
        self.temp_log_file = tempfile.NamedTemporaryFile(delete=False, suffix='.log')
        self.temp_log_file.close()
        
    def tearDown(self):
        """Clean up test fixtures"""
        # Remove temporary log file
        if os.path.exists(self.temp_log_file.name):
            os.unlink(self.temp_log_file.name)
    
    def test_setup_logging_default(self):
        """Test logging setup with default configuration"""
        setup_logging()
        
        # Check that root logger is configured
        root_logger = logging.getLogger()
        self.assertTrue(len(root_logger.handlers) > 0)
    
    def test_get_logger(self):
        """Test get_logger function"""
        logger = get_logger('test_module')
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, 'test_module')
    
    def test_set_log_level(self):
        """Test dynamically changing log level"""
        setup_logging()
        
        # Change to DEBUG level
        set_log_level('DEBUG')
        
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.DEBUG)
    
    def test_add_file_handler(self):
        """Test adding additional file handler"""
        setup_logging()
        
        initial_handler_count = len(logging.getLogger().handlers)
        
        # Add file handler
        add_file_handler(self.temp_log_file.name, 'INFO')
        
        # Check that handler was added
        new_handler_count = len(logging.getLogger().handlers)
        self.assertEqual(new_handler_count, initial_handler_count + 1)
    
    def test_custom_config(self):
        """Test logging setup with custom configuration"""
        custom_config = {
            'level': 'WARNING',
            'console_enabled': True,
            'file_enabled': False,
            'format': 'TEST: %(message)s'
        }
        
        setup_logging(custom_config)
        
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.WARNING)
    
    def test_file_logging_writes(self):
        """Test that file logging actually writes to file"""
        config = {
            'level': 'INFO',
            'console_enabled': False,
            'file_enabled': True,
            'file_path': self.temp_log_file.name
        }
        
        setup_logging(config)
        
        logger = get_logger('test')
        logger.info('Test message')
        
        # Force handlers to flush
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        # Check if file was written
        self.assertTrue(os.path.exists(self.temp_log_file.name))
        with open(self.temp_log_file.name, 'r') as f:
            content = f.read()
            self.assertIn('Test message', content)


if __name__ == '__main__':
    unittest.main()
