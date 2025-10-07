"""
Unit tests voor ArXiv client module
"""

import unittest
from unittest.mock import Mock, patch

from ..arxiv import ArxivClient


class TestArxivClient(unittest.TestCase):
    
    def setUp(self):
        """Setup test fixtures"""
        self.client = ArxivClient()
    
    def test_client_initialization(self):
        """Test ArxivClient initializes correctly"""
        self.assertIsNotNone(self.client.client)
        self.assertIsNotNone(self.client.logger)
        self.assertEqual(self.client.last_request_time, 0)
    
    @patch('time.sleep')
    def test_rate_limiting(self, mock_sleep):
        """Test rate limiting enforcement"""
        # First call should not sleep
        self.client._enforce_rate_limit()
        mock_sleep.assert_not_called()
        
        # Second immediate call should trigger sleep
        self.client._enforce_rate_limit()
        mock_sleep.assert_called_once()
    
    @patch('arxiv.Client')
    def test_search_papers_basic(self, mock_arxiv_client):
        """Test basic paper search functionality"""
        # Mock arxiv response
        mock_result = Mock()
        mock_result.entry_id = "http://arxiv.org/abs/2023.12345v1"
        mock_result.title = "Test Paper"
        mock_result.summary = "Test abstract"
        mock_result.authors = [Mock(name="Test Author")]
        mock_result.published.isoformat.return_value = "2023-01-01T00:00:00"
        mock_result.pdf_url = "http://arxiv.org/pdf/2023.12345v1"
        
        mock_client_instance = Mock()
        mock_client_instance.results.return_value = [mock_result]
        mock_arxiv_client.return_value = mock_client_instance
        
        # Create new client with mocked arxiv
        client = ArxivClient()
        
        # Test search
        with patch.object(client, '_enforce_rate_limit'):
            papers = client.search_papers("test query", max_results=1)
        
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]['arxiv_id'], "2023.12345v1")
        self.assertEqual(papers[0]['title'], "Test Paper")


if __name__ == '__main__':
    unittest.main()
