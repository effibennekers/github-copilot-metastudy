"""
Unit tests voor PDF processor module
"""

import unittest
from unittest.mock import Mock, patch, mock_open
import tempfile
import os
from pathlib import Path

from ..pdf import PDFProcessor


class TestPDFProcessor(unittest.TestCase):
    
    def setUp(self):
        """Setup test fixtures with temporary directories"""
        self.temp_pdf_dir = tempfile.mkdtemp()
        self.temp_md_dir = tempfile.mkdtemp()
        self.processor = PDFProcessor(self.temp_pdf_dir, self.temp_md_dir)
        
    def tearDown(self):
        """Clean up temporary directories"""
        import shutil
        shutil.rmtree(self.temp_pdf_dir)
        shutil.rmtree(self.temp_md_dir)
    
    def test_processor_initialization(self):
        """Test PDFProcessor initializes correctly"""
        self.assertTrue(self.processor.pdf_dir.exists())
        self.assertTrue(self.processor.md_dir.exists())
        self.assertIsNotNone(self.processor.logger)
    
    @patch('time.sleep')
    def test_rate_limiting(self, mock_sleep):
        """Test download rate limiting enforcement"""
        # First call should not sleep
        self.processor._enforce_download_rate_limit()
        mock_sleep.assert_not_called()
        
        # Second immediate call should trigger sleep
        self.processor._enforce_download_rate_limit()
        mock_sleep.assert_called_once()
    
    @patch('requests.get')
    @patch('time.sleep')
    def test_download_pdf_success(self, mock_sleep, mock_get):
        """Test successful PDF download"""
        # Mock successful response
        mock_response = Mock()
        mock_response.headers = {'content-type': 'application/pdf'}
        mock_response.iter_content.return_value = [b'fake pdf content']
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.processor.download_pdf('test.123v1', 'http://test.url/test.pdf')
        
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith('test.123v1.pdf'))
        mock_get.assert_called_once()
    
    @patch('requests.get')
    @patch('time.sleep')
    def test_download_pdf_failure(self, mock_sleep, mock_get):
        """Test PDF download failure handling"""
        # Mock failed response
        mock_get.side_effect = Exception("Network error")
        
        result = self.processor.download_pdf('test.123v1', 'http://test.url/test.pdf')
        
        self.assertIsNone(result)
    
    def test_file_already_exists(self):
        """Test PDF download when file already exists"""
        # Create a fake existing PDF
        pdf_path = Path(self.temp_pdf_dir) / "test.123v1.pdf"
        with open(pdf_path, 'wb') as f:
            f.write(b'fake pdf content' * 100)  # Make it big enough to pass size check
        
        result = self.processor.download_pdf('test.123v1', 'http://test.url/test.pdf')
        
        self.assertIsNotNone(result)
        self.assertEqual(result, str(pdf_path))
    
    @patch('subprocess.run')
    def test_pandoc_conversion_success(self, mock_run):
        """Test successful pandoc conversion"""
        # Create fake PDF file
        pdf_path = Path(self.temp_pdf_dir) / "test.123v1.pdf"
        with open(pdf_path, 'wb') as f:
            f.write(b'fake pdf content' * 100)
        
        # Mock successful pandoc run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Mock markdown file creation
        md_path = Path(self.temp_md_dir) / "test.123v1.md"
        
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = 500  # Reasonable size
                
                result = self.processor.pdf_to_markdown(str(pdf_path), 'test.123v1')
        
        self.assertIsNotNone(result)
        mock_run.assert_called_once()
    
    def test_cleanup_failed_files(self):
        """Test cleanup of failed/corrupted files"""
        # Create small (failed) PDF
        small_pdf = Path(self.temp_pdf_dir) / "small.pdf"
        with open(small_pdf, 'wb') as f:
            f.write(b'small')  # Too small
        
        # Create small (failed) markdown
        small_md = Path(self.temp_md_dir) / "small.md"
        with open(small_md, 'w') as f:
            f.write('x')  # Too small
        
        self.processor.cleanup_failed_files()
        
        # Files should be removed
        self.assertFalse(small_pdf.exists())
        self.assertFalse(small_md.exists())


if __name__ == '__main__':
    unittest.main()
