"""
Unit tests voor database models module
"""

import unittest

from ..database import PaperDatabase


class TestPaperDatabase(unittest.TestCase):

    def setUp(self):
        """Setup test fixtures"""
        self.db = PaperDatabase()

    def tearDown(self):
        """Clean up after tests"""
        pass

    def test_database_initialization(self):
        """Test database initializes correctly"""
        self.assertIsNotNone(self.db)

    def test_paper_exists_false(self):
        """Test paper_exists returns False for non-existent paper"""
        result = self.db.paper_exists("nonexistent_id")
        self.assertFalse(result)

    def test_insert_and_exists_paper(self):
        """Test inserting paper and checking existence"""
        paper_data = {
            "arxiv_id": "test.12345v1",
            "title": "Test Paper Title",
            "abstract": "Test abstract content",
            "authors": ["Test Author 1", "Test Author 2"],
            "published_date": "2023-01-01T00:00:00",
            "url": "http://arxiv.org/abs/test.12345v1",
            "pdf_url": "http://arxiv.org/pdf/test.12345v1",
        }

        # Insert paper
        self.db.insert_paper(paper_data)

        # Check existence
        self.assertTrue(self.db.paper_exists("test.12345v1"))

    def test_get_papers_by_status(self):
        """Test retrieving papers by status"""
        # Insert test paper
        paper_data = {"arxiv_id": "test.12345v1", "title": "Test Paper", "authors": ["Test Author"]}
        self.db.insert_paper(paper_data)

        # Get pending papers
        pending = self.db.get_papers_by_status(download_status="PENDING")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["arxiv_id"], "test.12345v1")

    def test_update_paper_status(self):
        """Test updating paper status"""
        # Insert test paper
        paper_data = {"arxiv_id": "test.12345v1", "title": "Test Paper", "authors": ["Test Author"]}
        self.db.insert_paper(paper_data)

        # Update status
        self.db.update_paper_status("test.12345v1", download_status="DOWNLOADED")

        # Verify update
        downloaded = self.db.get_papers_by_status(download_status="DOWNLOADED")
        self.assertEqual(len(downloaded), 1)

    def test_get_statistics(self):
        """Test getting database statistics"""
        # Insert test papers
        for i in range(3):
            paper_data = {
                "arxiv_id": f"test.{i}v1",
                "title": f"Test Paper {i}",
                "authors": ["Test Author"],
            }
            self.db.insert_paper(paper_data)

        stats = self.db.get_statistics()
        self.assertEqual(stats["total_papers"], 3)
        self.assertIn("download_status", stats)
        self.assertIn("llm_status", stats)


if __name__ == "__main__":
    unittest.main()
