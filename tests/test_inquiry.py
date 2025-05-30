"""
Test suite for Inquiry class functionality.
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
    config.api_key = "test-key"  # Set a test API key
    return config


@pytest.fixture
def sample_document():
    """Create a temporary test document."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        tmp.write("This is a test document written by Test Author in 2023.")
        tmp_path = tmp.name
    
    yield tmp_path
    
    # Cleanup
    os.unlink(tmp_path)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client that returns proper JSON responses."""
    mock_client = MagicMock()
    
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"default": "Test Author"}'
    mock_client.chat.completions.create.return_value = mock_response
    
    # Mock models list
    mock_model = MagicMock()
    mock_model.id = "gpt-3.5-turbo"
    mock_client.models.list.return_value.data = [mock_model]
    
    return mock_client


class TestInquiryInitialization:
    """Test suite for Inquiry initialization."""
    
    def test_inquiry_with_string_question(self, mock_openai_client, test_config):
        """Test Inquiry initialization with string question."""
        inquiry = Inquiry(
            questions="Who is the author?",
            client=mock_openai_client,
            config=test_config
        )
        
        assert len(inquiry.questions) == 1
        assert "default" in inquiry.questions
        assert inquiry.questions["default"]["question"] == "Who is the author?"
        assert inquiry.questions["default"]["type"] == "str"
    
    def test_inquiry_with_list_questions(self, mock_openai_client, test_config):
        """Test Inquiry initialization with list of questions."""
        questions = ["Who is the author?", "What is the title?"]
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config
        )
        
        assert len(inquiry.questions) == 2
        assert "question_1" in inquiry.questions
        assert "question_2" in inquiry.questions
        assert inquiry.questions["question_1"]["question"] == "Who is the author?"
        assert inquiry.questions["question_2"]["question"] == "What is the title?"
    
    def test_inquiry_with_dict_questions(self, mock_openai_client, test_config):
        """Test Inquiry initialization with dictionary questions."""
        questions = {
            "author": {
                "question": "Who is the author?",
                "type": "str"
            },
            "title": {
                "question": "What is the title?",
                "type": "str"
            }
        }
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config
        )
        
        assert len(inquiry.questions) == 2
        assert "author" in inquiry.questions
        assert "title" in inquiry.questions
        assert inquiry.questions["author"]["question"] == "Who is the author?"
        assert inquiry.questions["title"]["question"] == "What is the title?"
    
    def test_inquiry_without_api_key_raises_error(self):
        """Test that Inquiry raises error when no API key is provided."""
        config = Config()
        config.api_key = None  # No API key
        
        with pytest.raises(RuntimeError, match="Failed to initialize OpenAI client"):
            Inquiry(questions="Test question?", config=config)
    
    def test_inquiry_with_invalid_questions_raises_error(self, test_config):
        """Test that Inquiry raises error with invalid questions."""
        with pytest.raises(ValueError):
            Inquiry(questions=123, config=test_config)  # Invalid type


class TestInquiryDocumentProcessing:
    """Test suite for document processing functionality."""
    
    def test_process_document_success(self, mock_openai_client, test_config, sample_document):
        """Test successful document processing."""
        inquiry = Inquiry(
            questions="Who is the author?",
            client=mock_openai_client,
            config=test_config
        )
        
        result = inquiry.process_document(sample_document)
        
        assert isinstance(result, dict)
        assert "default" in result
        assert result["default"] == "Test Author"
        assert "_document_path" in result
        assert "_document_name" in result
        assert result["_document_path"] == sample_document
    
    def test_process_document_nonexistent_file(self, mock_openai_client, test_config):
        """Test processing non-existent document."""
        inquiry = Inquiry(
            questions="Who is the author?",
            client=mock_openai_client,
            config=test_config
        )
        
        with pytest.raises(RuntimeError, match="Failed to process document"):
            inquiry.process_document("/nonexistent/file.txt")
    
    def test_process_document_no_questions(self, mock_openai_client, test_config, sample_document):
        """Test processing document with no questions defined."""
        inquiry = Inquiry(
            questions={},
            client=mock_openai_client,
            config=test_config
        )
        
        with pytest.raises(ValueError, match="No questions defined"):
            inquiry.process_document(sample_document)
    
    def test_process_documents_single_file(self, mock_openai_client, test_config, sample_document):
        """Test processing single document via process_documents."""
        inquiry = Inquiry(
            questions="Who is the author?",
            client=mock_openai_client,
            config=test_config
        )
        
        result = inquiry.process_documents(sample_document)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert "default" in result.columns
        assert result.iloc[0]["default"] == "Test Author"
    
    def test_process_documents_list(self, mock_openai_client, test_config, sample_document):
        """Test processing list of documents."""
        inquiry = Inquiry(
            questions="Who is the author?",
            client=mock_openai_client,
            config=test_config
        )
        
        # Create second test document
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp2:
            tmp2.write("Another test document by Another Author.")
            tmp2_path = tmp2.name
        
        try:
            result = inquiry.process_documents([sample_document, tmp2_path])
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2
            assert "default" in result.columns
        finally:
            os.unlink(tmp2_path)
    
    def test_process_documents_invalid_input(self, mock_openai_client, test_config):
        """Test processing documents with invalid input."""
        inquiry = Inquiry(
            questions="Who is the author?",
            client=mock_openai_client,
            config=test_config
        )
        
        with pytest.raises(ValueError, match="Documents must be a string path or list of paths"):
            inquiry.process_documents(123)  # Invalid type


class TestInquiryAPIHandling:
    """Test suite for API call handling."""
    
    def test_api_retry_on_rate_limit(self, test_config, sample_document):
        """Test API retry logic on rate limit error."""
        mock_client = MagicMock()
        
        # Mock rate limit error on first call, success on second
        mock_client.chat.completions.create.side_effect = [
            Exception("Rate limit exceeded"),  # First call fails
            MagicMock(choices=[MagicMock(message=MagicMock(content='{"default": "Test Author"}'))])  # Second call succeeds
        ]
        
        # Mock models list
        mock_model = MagicMock()
        mock_model.id = "gpt-3.5-turbo"
        mock_client.models.list.return_value.data = [mock_model]
        
        inquiry = Inquiry(
            questions="Who is the author?",
            client=mock_client,
            config=test_config
        )
        
        # Should succeed after retry
        result = inquiry.process_document(sample_document)
        assert "default" in result
    
    def test_api_failure_after_retries(self, test_config, sample_document):
        """Test API failure after all retries exhausted."""
        mock_client = MagicMock()
        
        # Mock persistent failure for both APIs
        mock_client.chat.completions.create.side_effect = Exception("Persistent API error")
        mock_client.beta.chat.completions.parse.side_effect = Exception("Persistent API error")
        
        # Mock models list
        mock_model = MagicMock()
        mock_model.id = "gpt-3.5-turbo"
        mock_client.models.list.return_value.data = [mock_model]
        
        inquiry = Inquiry(
            questions="Who is the author?",
            client=mock_client,
            config=test_config
        )
        
        with pytest.raises(RuntimeError, match="Failed to process document"):
            inquiry.process_document(sample_document)


class TestInquiryFromFile:
    """Test suite for creating Inquiry from file."""
    
    def test_from_file_txt(self, mock_openai_client, test_config):
        """Test creating Inquiry from text file."""
        # Create temporary questions file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("Who is the author?\nWhat is the title?\n")
            tmp_path = tmp.name
        
        try:
            inquiry = Inquiry.from_file(tmp_path, client=mock_openai_client, config=test_config)
            
            assert len(inquiry.questions) == 2
            assert any("author" in q["question"].lower() for q in inquiry.questions.values())
            assert any("title" in q["question"].lower() for q in inquiry.questions.values())
        finally:
            os.unlink(tmp_path)
    
    def test_from_file_csv(self, mock_openai_client, test_config):
        """Test creating Inquiry from CSV file."""
        # Create temporary CSV questions file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            tmp.write("question,field_name,data_type\n")
            tmp.write("\"Who is the author?\",author,str\n")
            tmp.write("\"What is the title?\",title,str\n")
            tmp_path = tmp.name
        
        try:
            inquiry = Inquiry.from_file(tmp_path, client=mock_openai_client, config=test_config)
            
            assert len(inquiry.questions) == 2
            assert "author" in inquiry.questions
            assert "title" in inquiry.questions
            assert inquiry.questions["author"]["type"] == "str"
            assert inquiry.questions["title"]["type"] == "str"
        finally:
            os.unlink(tmp_path)
    
    def test_from_file_nonexistent(self, test_config):
        """Test creating Inquiry from non-existent file."""
        with pytest.raises(FileNotFoundError):
            Inquiry.from_file("/nonexistent/file.txt", config=test_config)


class TestInquiryQuestionNormalization:
    """Test suite for question normalization."""
    
    def test_normalize_string_question(self, mock_openai_client, test_config):
        """Test normalizing string question."""
        inquiry = Inquiry(
            questions="Who is the author?",
            client=mock_openai_client,
            config=test_config
        )
        
        normalized = inquiry.normalize_questions("Who is the author?")
        
        assert len(normalized) == 1
        assert "default" in normalized
        assert normalized["default"]["question"] == "Who is the author?"
        assert normalized["default"]["type"] == "str"
    
    def test_normalize_list_questions(self, mock_openai_client, test_config):
        """Test normalizing list of questions."""
        inquiry = Inquiry(
            questions=["Who is the author?", "What is the title?"],
            client=mock_openai_client,
            config=test_config
        )
        
        questions = ["Who is the author?", "What is the title?"]
        normalized = inquiry.normalize_questions(questions)
        
        assert len(normalized) == 2
        assert "question_1" in normalized
        assert "question_2" in normalized
        assert normalized["question_1"]["question"] == "Who is the author?"
        assert normalized["question_2"]["question"] == "What is the title?"
    
    def test_normalize_dict_questions(self, mock_openai_client, test_config):
        """Test normalizing dictionary questions."""
        inquiry = Inquiry(
            questions={"author": {"question": "Who is the author?", "type": "str"}},
            client=mock_openai_client,
            config=test_config
        )
        
        questions = {
            "author": {"question": "Who is the author?", "type": "str"},
            "title": {"question": "What is the title?", "type": "str"}
        }
        normalized = inquiry.normalize_questions(questions)
        
        assert len(normalized) == 2
        assert "author" in normalized
        assert "title" in normalized
        assert normalized["author"]["question"] == "Who is the author?"
        assert normalized["title"]["question"] == "What is the title?"
    
    def test_normalize_invalid_questions(self, mock_openai_client, test_config):
        """Test normalizing invalid questions."""
        inquiry = Inquiry(
            questions="Test",
            client=mock_openai_client,
            config=test_config
        )
        
        with pytest.raises(ValueError):
            inquiry.normalize_questions(123)  # Invalid type


class TestInquiryIntegration:
    """Integration tests for Inquiry functionality."""
    
    def test_end_to_end_processing(self, mock_openai_client, test_config):
        """Test complete end-to-end document processing."""
        # Create test document
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("Research Paper: AI in Healthcare\nAuthor: Dr. Jane Smith\nPublished: 2023")
            doc_path = tmp.name
        
        try:
            # Create inquiry with multiple questions
            questions = {
                "title": {"question": "What is the title?", "type": "str"},
                "author": {"question": "Who is the author?", "type": "str"},
                "year": {"question": "What year was it published?", "type": "int"}
            }
            
            # Mock API response with all fields
            mock_openai_client.chat.completions.create.return_value.choices[0].message.content = json.dumps({
                "title": "AI in Healthcare",
                "author": "Dr. Jane Smith",
                "year": 2023
            })
            
            inquiry = Inquiry(
                questions=questions,
                client=mock_openai_client,
                config=test_config
            )
            
            # Process document
            result = inquiry.process_document(doc_path)
            
            # Verify results
            assert result["title"] == "AI in Healthcare"
            assert result["author"] == "Dr. Jane Smith"
            assert result["year"] == 2023
            assert result["_document_path"] == doc_path
            assert "_document_name" in result
            
        finally:
            os.unlink(doc_path)
