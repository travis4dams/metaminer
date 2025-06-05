"""
Test suite for the new text processing functionality in Inquiry class.
"""
import pytest
import tempfile
import os
import json
import pandas as pd
from unittest.mock import MagicMock, patch
from metaminer.inquiry import Inquiry
from metaminer.config import Config


@pytest.fixture
def test_config():
    """Test configuration with mocked settings."""
    config = Config()
    config.api_key = "test-key"
    return config


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client that returns proper JSON responses."""
    mock_client = MagicMock()
    
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"author": "Test Author", "title": "Test Title"}'
    mock_client.chat.completions.create.return_value = mock_response
    
    # Mock the structured output API to fail (so it falls back to JSON mode)
    mock_client.beta.chat.completions.parse.side_effect = AttributeError("Structured output not available")
    
    # Mock models list
    mock_model = MagicMock()
    mock_model.id = "gpt-3.5-turbo"
    mock_client.models.list.return_value.data = [mock_model]
    
    return mock_client


class TestTextProcessing:
    """Test suite for the new process_text functionality."""
    
    def test_process_single_text_string(self, mock_openai_client, test_config):
        """Test processing a single text string."""
        questions = {
            "author": {"question": "Who is the author?", "type": "str"},
            "title": {"question": "What is the title?", "type": "str"}
        }
        
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config
        )
        
        text = "This is a research paper titled 'AI in Healthcare' written by Dr. Jane Smith."
        result = inquiry.process_text(text)
        
        assert isinstance(result, dict)
        assert "author" in result
        assert "title" in result
        assert result["author"] == "Test Author"
        assert result["title"] == "Test Title"
    
    def test_process_single_text_with_metadata(self, mock_openai_client, test_config):
        """Test processing a single text string with metadata."""
        questions = {
            "author": {"question": "Who is the author?", "type": "str"}
        }
        
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config
        )
        
        text = "This is a research paper written by Dr. Jane Smith."
        metadata = {"source": "test_source", "category": "research"}
        
        result = inquiry.process_text(text, metadata)
        
        assert isinstance(result, dict)
        assert "author" in result
        assert "source" in result
        assert "category" in result
        assert result["source"] == "test_source"
        assert result["category"] == "research"
    
    def test_process_multiple_texts(self, mock_openai_client, test_config):
        """Test processing multiple text strings."""
        questions = {
            "author": {"question": "Who is the author?", "type": "str"}
        }
        
        # Mock different responses for each text
        mock_responses = [
            MagicMock(choices=[MagicMock(message=MagicMock(content='{"author": "Author One"}'))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content='{"author": "Author Two"}'))])
        ]
        mock_openai_client.chat.completions.create.side_effect = mock_responses
        
        # Disable type inference to avoid consuming mock responses
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config,
            infer_types=False
        )
        
        texts = [
            "First paper by Author One",
            "Second paper by Author Two"
        ]
        
        results = inquiry.process_texts(texts)
        
        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["author"] == "Author One"
        assert results[1]["author"] == "Author Two"
    
    def test_process_multiple_texts_with_metadata_list(self, mock_openai_client, test_config):
        """Test processing multiple texts with corresponding metadata list."""
        questions = {
            "author": {"question": "Who is the author?", "type": "str"}
        }
        
        # Mock different responses for each text
        mock_responses = [
            MagicMock(choices=[MagicMock(message=MagicMock(content='{"author": "Author One"}'))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content='{"author": "Author Two"}'))])
        ]
        mock_openai_client.chat.completions.create.side_effect = mock_responses
        
        # Disable type inference to avoid consuming mock responses
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config,
            infer_types=False
        )
        
        texts = [
            "First paper by Author One",
            "Second paper by Author Two"
        ]
        
        metadata = [
            {"source": "journal_a", "year": 2023},
            {"source": "journal_b", "year": 2024}
        ]
        
        results = inquiry.process_texts(texts, metadata)
        
        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["author"] == "Author One"
        assert results[0]["source"] == "journal_a"
        assert results[0]["year"] == 2023
        assert results[1]["author"] == "Author Two"
        assert results[1]["source"] == "journal_b"
        assert results[1]["year"] == 2024
    
    def test_process_multiple_texts_with_single_metadata_dict(self, mock_openai_client, test_config):
        """Test processing multiple texts with single metadata dict applied to all."""
        questions = {
            "author": {"question": "Who is the author?", "type": "str"}
        }
        
        # Mock different responses for each text
        mock_responses = [
            MagicMock(choices=[MagicMock(message=MagicMock(content='{"author": "Author One"}'))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content='{"author": "Author Two"}'))])
        ]
        mock_openai_client.chat.completions.create.side_effect = mock_responses
        
        # Disable type inference to avoid consuming mock responses
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config,
            infer_types=False
        )
        
        texts = [
            "First paper by Author One",
            "Second paper by Author Two"
        ]
        
        metadata = {"conference": "AI Conference 2024"}
        
        results = inquiry.process_texts(texts, metadata)
        
        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["author"] == "Author One"
        assert results[0]["conference"] == "AI Conference 2024"
        assert results[1]["author"] == "Author Two"
        assert results[1]["conference"] == "AI Conference 2024"
    
    def test_process_text_empty_string_raises_error(self, mock_openai_client, test_config):
        """Test that processing empty text raises ValueError."""
        questions = {"author": {"question": "Who is the author?", "type": "str"}}
        
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config
        )
        
        with pytest.raises(ValueError, match="Text content cannot be empty"):
            inquiry.process_text("")
    
    def test_process_text_no_questions_raises_error(self, mock_openai_client, test_config):
        """Test that processing text with no questions raises ValueError."""
        inquiry = Inquiry(
            questions={},
            client=mock_openai_client,
            config=test_config
        )
        
        with pytest.raises(ValueError, match="No questions defined"):
            inquiry.process_text("Some text")
    
    def test_process_text_invalid_input_type_raises_error(self, mock_openai_client, test_config):
        """Test that invalid input type raises ValueError."""
        questions = {"author": {"question": "Who is the author?", "type": "str"}}
        
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config
        )
        
        with pytest.raises(ValueError, match=r"process_text\(\) only accepts single strings\. Use process_texts\(\) for lists/iterables\."):
            inquiry.process_text(123)  # Invalid type
    
    def test_process_text_list_with_non_string_raises_error(self, mock_openai_client, test_config):
        """Test that list containing non-strings raises ValueError."""
        questions = {"author": {"question": "Who is the author?", "type": "str"}}
        
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config
        )
        
        with pytest.raises(ValueError, match=r"process_text\(\) only accepts single strings\. Use process_texts\(\) for lists/iterables\."):
            inquiry.process_text(["Valid text", 123, "Another valid text"])
    
    def test_process_text_metadata_length_mismatch_raises_error(self, mock_openai_client, test_config):
        """Test that metadata list length mismatch raises ValueError."""
        questions = {"author": {"question": "Who is the author?", "type": "str"}}
        
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config
        )
        
        texts = ["Text one", "Text two"]
        metadata = [{"source": "A"}]  # Only one metadata for two texts
        
        with pytest.raises(ValueError, match=r"process_text\(\) only accepts single strings\. Use process_texts\(\) for lists/iterables\."):
            inquiry.process_text(texts, metadata)
    
    def test_process_text_continues_on_individual_failures(self, mock_openai_client, test_config):
        """Test that processing continues when individual texts fail."""
        questions = {"author": {"question": "Who is the author?", "type": "str"}}
        
        # Mock first call to fail, second to succeed
        mock_responses = [
            Exception("API Error"),  # First call fails
            MagicMock(choices=[MagicMock(message=MagicMock(content='{"author": "Author Two"}'))])  # Second succeeds
        ]
        mock_openai_client.chat.completions.create.side_effect = mock_responses
        
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config
        )
        
        texts = ["First text", "Second text"]
        results = inquiry.process_texts(texts)
        
        # Should only have one result (the successful one)
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["author"] == "Author Two"


class TestDocumentProcessingWithTextMethod:
    """Test that document processing now uses the new text processing method."""
    
    def test_process_document_uses_text_method(self, mock_openai_client, test_config):
        """Test that process_document now uses the new _process_single_text method."""
        questions = {"author": {"question": "Who is the author?", "type": "str"}}
        
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config
        )
        
        # Create a temporary test document
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("This is a test document written by Test Author.")
            tmp_path = tmp.name
        
        try:
            # Mock the API response
            mock_openai_client.chat.completions.create.return_value.choices[0].message.content = '{"author": "Test Author"}'
            
            result = inquiry.process_document(tmp_path)
            
            # Verify the result includes both extracted data and document metadata
            assert isinstance(result, dict)
            assert "author" in result
            assert "_document_path" in result
            assert "_document_name" in result
            assert result["author"] == "Test Author"
            assert result["_document_path"] == tmp_path
            assert result["_document_name"] == os.path.basename(tmp_path)
            
        finally:
            os.unlink(tmp_path)


class TestIntegrationWithExistingAPI:
    """Test that existing API still works with the new implementation."""
    
    def test_backward_compatibility_process_documents(self, mock_openai_client, test_config):
        """Test that process_documents still works as expected."""
        questions = {"author": {"question": "Who is the author?", "type": "str"}}
        
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config
        )
        
        # Create temporary test documents
        docs = []
        for i in range(2):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                tmp.write(f"This is test document {i+1} written by Author {i+1}.")
                docs.append(tmp.name)
        
        try:
            # Mock API responses
            mock_responses = [
                MagicMock(choices=[MagicMock(message=MagicMock(content='{"author": "Author 1"}'))]),
                MagicMock(choices=[MagicMock(message=MagicMock(content='{"author": "Author 2"}'))])
            ]
            mock_openai_client.chat.completions.create.side_effect = mock_responses
            
            result = inquiry.process_documents(docs)
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2
            assert "author" in result.columns
            assert "_document_path" in result.columns
            assert "_document_name" in result.columns
            
        finally:
            for doc in docs:
                os.unlink(doc)
