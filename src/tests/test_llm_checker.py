import unittest
from unittest.mock import patch, Mock

from src.llm import LLMChecker


class TestLLMCheckerClassification(unittest.TestCase):
    def setUp(self):
        self.checker = LLMChecker()
        # Force enable in case config disables it
        self.checker.config["enabled"] = True

    @patch("src.llm.checker.ollama.Client")
    def test_classify_true_json(self, mock_client_cls):
        mock_client = Mock()
        mock_client.chat.return_value = {"message": {"content": '{"answer": true}'}}
        mock_client_cls.return_value = mock_client

        result = self.checker.classify_title_abstract_boolean(
            question="Gaat dit over GitHub Copilot?",
            title="A study on GitHub Copilot",
            abstract="We analyze the impact of GitHub Copilot on productivity.",
        )
        self.assertTrue(result)

    @patch("src.llm.checker.ollama.Client")
    def test_classify_false_json(self, mock_client_cls):
        mock_client = Mock()
        mock_client.chat.return_value = {"message": {"content": '{"answer": false}'}}
        mock_client_cls.return_value = mock_client

        result = self.checker.classify_title_abstract_boolean(
            question="Gaat dit over GitHub Copilot?",
            title="A study on climate",
            abstract="We analyze climate data and patterns.",
        )
        self.assertFalse(result)

    @patch("src.llm.checker.ollama.Client")
    def test_classify_fallback_yes(self, mock_client_cls):
        mock_client = Mock()
        mock_client.chat.return_value = {"message": {"content": "yes"}}
        mock_client_cls.return_value = mock_client

        result = self.checker.classify_title_abstract_boolean(
            question="Gaat dit over GitHub Copilot?",
            title="GitHub Copilot user study",
            abstract="We report findings from a user study on Copilot.",
        )
        self.assertTrue(result)

    @patch("src.llm.checker.ollama.Client")
    def test_missing_fields(self, mock_client_cls):
        # Client shouldn't be called when inputs are missing
        result = self.checker.classify_title_abstract_boolean(
            question="Gaat dit over GitHub Copilot?", title="", abstract="Some abstract"
        )
        self.assertFalse(result)
        mock_client_cls.assert_not_called()

    @patch("src.llm.checker.ollama.Client")
    def test_metadata_helper(self, mock_client_cls):
        mock_client = Mock()
        mock_client.chat.return_value = {"message": {"content": '{"answer": true}'}}
        mock_client_cls.return_value = mock_client

        record = {"title": "Lab study on Copilot", "abstract": "We conducted a lab study."}
        result = self.checker.classify_metadata_record_boolean(
            question="Gaat dit over GitHub Copilot?", metadata_record=record
        )
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
