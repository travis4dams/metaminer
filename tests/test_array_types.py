"""
Test suite for array type functionality.
"""
import pytest
import tempfile
import os
import json
import pandas as pd
from unittest.mock import MagicMock, patch
from metaminer.inquiry import Inquiry
from metaminer.config import Config
from metaminer.schema_builder import build_schema_from_questions, _parse_array_type, _get_python_type
from metaminer.question_parser import parse_questions_from_file, _is_valid_array_type
from typing import List


@pytest.fixture
def test_config():
    """Test configuration with mocked settings."""
    config = Config()
    config.api_key = "test-key"  # Set a test API key
    return config


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client that returns proper JSON responses for array types."""
    mock_client = MagicMock()
    
    # Mock successful API response with array data
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "authors": ["Dr. Jane Smith", "Dr. John Doe"],
        "keywords": ["AI", "Healthcare", "Machine Learning"],
        "page_numbers": [1, 2, 3, 4, 5]
    })
    mock_client.chat.completions.create.return_value = mock_response
    
    # Mock the structured output API to fail (so it falls back to JSON mode)
    mock_client.beta.chat.completions.parse.side_effect = AttributeError("Structured output not available")
    
    # Mock models list
    mock_model = MagicMock()
    mock_model.id = "gpt-3.5-turbo"
    mock_client.models.list.return_value.data = [mock_model]
    
    return mock_client


class TestArrayTypeParsing:
    """Test suite for array type parsing functionality."""
    
    def test_parse_array_type_valid(self):
        """Test parsing valid array type specifications."""
        # Test valid array types
        is_array, base_type = _parse_array_type("list(str)")
        assert is_array is True
        assert base_type == "str"
        
        is_array, base_type = _parse_array_type("list(int)")
        assert is_array is True
        assert base_type == "int"
        
        is_array, base_type = _parse_array_type("list(date)")
        assert is_array is True
        assert base_type == "date"
        
        # Test with extra whitespace
        is_array, base_type = _parse_array_type("  list( str )  ")
        assert is_array is True
        assert base_type == "str"
    
    def test_parse_array_type_invalid(self):
        """Test parsing invalid array type specifications."""
        # Test non-array types
        is_array, base_type = _parse_array_type("str")
        assert is_array is False
        assert base_type == "str"
        
        is_array, base_type = _parse_array_type("int")
        assert is_array is False
        assert base_type == "int"
        
        # Test malformed array types
        is_array, base_type = _parse_array_type("list(")
        assert is_array is False
        
        is_array, base_type = _parse_array_type("liststr)")
        assert is_array is False
    
    def test_get_python_type_arrays(self):
        """Test getting Python types for array specifications."""
        # Test array types
        assert _get_python_type("list(str)") == List[str]
        assert _get_python_type("list(int)") == List[int]
        assert _get_python_type("list(float)") == List[float]
        assert _get_python_type("list(bool)") == List[bool]
        
        # Test non-array types (should work as before)
        assert _get_python_type("str") == str
        assert _get_python_type("int") == int
    
    def test_is_valid_array_type(self):
        """Test validation of array type specifications."""
        # Valid array types
        assert _is_valid_array_type("list(str)") is True
        assert _is_valid_array_type("list(int)") is True
        assert _is_valid_array_type("list(float)") is True
        assert _is_valid_array_type("list(bool)") is True
        assert _is_valid_array_type("list(date)") is True
        assert _is_valid_array_type("list(datetime)") is True
        
        # Invalid array types
        assert _is_valid_array_type("list(invalid)") is False
        assert _is_valid_array_type("str") is False
        assert _is_valid_array_type("list(") is False
        assert _is_valid_array_type("liststr)") is False


class TestArraySchemaBuilding:
    """Test suite for building schemas with array types."""
    
    def test_build_schema_with_arrays(self):
        """Test building Pydantic schema with array fields."""
        questions = {
            "authors": {
                "question": "Who are the authors?",
                "type": "list(str)",
                "output_name": "authors"
            },
            "keywords": {
                "question": "What are the keywords?",
                "type": "list(str)",
                "output_name": "keywords"
            },
            "page_numbers": {
                "question": "What are the page numbers?",
                "type": "list(int)",
                "output_name": "page_numbers"
            }
        }
        
        schema = build_schema_from_questions(questions)
        
        # Verify schema class was created
        assert schema is not None
        assert hasattr(schema, '__name__')
        assert hasattr(schema, 'model_fields')
        
        # Verify fields are present
        assert 'authors' in schema.model_fields
        assert 'keywords' in schema.model_fields
        assert 'page_numbers' in schema.model_fields
        
        # Test creating an instance
        instance = schema(
            authors=["Dr. Jane Smith", "Dr. John Doe"],
            keywords=["AI", "Healthcare"],
            page_numbers=[1, 2, 3]
        )
        
        assert instance.authors == ["Dr. Jane Smith", "Dr. John Doe"]
        assert instance.keywords == ["AI", "Healthcare"]
        assert instance.page_numbers == [1, 2, 3]
    
    def test_build_schema_mixed_types(self):
        """Test building schema with both array and non-array types."""
        questions = {
            "title": {
                "question": "What is the title?",
                "type": "str",
                "output_name": "title"
            },
            "authors": {
                "question": "Who are the authors?",
                "type": "list(str)",
                "output_name": "authors"
            },
            "page_count": {
                "question": "How many pages?",
                "type": "int",
                "output_name": "page_count"
            }
        }
        
        schema = build_schema_from_questions(questions)
        
        # Test creating an instance with mixed types
        instance = schema(
            title="AI in Healthcare",
            authors=["Dr. Jane Smith", "Dr. John Doe"],
            page_count=25
        )
        
        assert instance.title == "AI in Healthcare"
        assert instance.authors == ["Dr. Jane Smith", "Dr. John Doe"]
        assert instance.page_count == 25


class TestArrayQuestionParsing:
    """Test suite for parsing questions with array types from files."""
    
    def test_parse_csv_with_array_types(self):
        """Test parsing CSV file with array type specifications."""
        # Create temporary CSV file with array types
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            tmp.write("question,field_name,data_type\n")
            tmp.write("\"Who are the authors?\",authors,list(str)\n")
            tmp.write("\"What are the keywords?\",keywords,list(str)\n")
            tmp.write("\"What are the page numbers?\",page_numbers,list(int)\n")
            tmp.write("\"What is the title?\",title,str\n")
            tmp_path = tmp.name
        
        try:
            questions = parse_questions_from_file(tmp_path)
            
            assert len(questions) == 4
            assert questions["authors"]["type"] == "list(str)"
            assert questions["keywords"]["type"] == "list(str)"
            assert questions["page_numbers"]["type"] == "list(int)"
            assert questions["title"]["type"] == "str"
            
        finally:
            os.unlink(tmp_path)
    
    def test_parse_csv_invalid_array_types(self):
        """Test parsing CSV file with invalid array type specifications."""
        # Create temporary CSV file with invalid array types
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            tmp.write("question,field_name,data_type\n")
            tmp.write("\"Who are the authors?\",authors,list(invalid)\n")
            tmp.write("\"What are the keywords?\",keywords,list(\n")
            tmp_path = tmp.name
        
        try:
            questions = parse_questions_from_file(tmp_path)
            
            # Invalid array types should fall back to str
            assert questions["authors"]["type"] == "str"
            assert questions["keywords"]["type"] == "str"
            
        finally:
            os.unlink(tmp_path)


class TestArrayInquiryIntegration:
    """Test suite for end-to-end array type functionality."""
    
    def test_inquiry_with_array_questions(self, mock_openai_client, test_config):
        """Test Inquiry with array type questions."""
        questions = {
            "authors": {
                "question": "Who are the authors?",
                "type": "list(str)"
            },
            "keywords": {
                "question": "What are the keywords?",
                "type": "list(str)"
            },
            "page_numbers": {
                "question": "What are the page numbers?",
                "type": "list(int)"
            }
        }
        
        inquiry = Inquiry(
            questions=questions,
            client=mock_openai_client,
            config=test_config
        )
        
        assert len(inquiry.questions) == 3
        assert inquiry.questions["authors"]["type"] == "list(str)"
        assert inquiry.questions["keywords"]["type"] == "list(str)"
        assert inquiry.questions["page_numbers"]["type"] == "list(int)"
    
    def test_process_document_with_arrays(self, mock_openai_client, test_config):
        """Test processing document with array type questions."""
        # Create test document
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("Research Paper: AI in Healthcare\n")
            tmp.write("Authors: Dr. Jane Smith, Dr. John Doe\n")
            tmp.write("Keywords: AI, Healthcare, Machine Learning\n")
            tmp.write("Pages: 1, 2, 3, 4, 5\n")
            doc_path = tmp.name
        
        try:
            questions = {
                "authors": {
                    "question": "Who are the authors?",
                    "type": "list(str)"
                },
                "keywords": {
                    "question": "What are the keywords?",
                    "type": "list(str)"
                },
                "page_numbers": {
                    "question": "What are the page numbers?",
                    "type": "list(int)"
                }
            }
            
            inquiry = Inquiry(
                questions=questions,
                client=mock_openai_client,
                config=test_config
            )
            
            # Process document
            result = inquiry.process_document(doc_path)
            
            # Verify results contain arrays
            assert "authors" in result
            assert "keywords" in result
            assert "page_numbers" in result
            assert isinstance(result["authors"], list)
            assert isinstance(result["keywords"], list)
            assert isinstance(result["page_numbers"], list)
            
        finally:
            os.unlink(doc_path)
    
    def test_inquiry_from_csv_with_arrays(self, mock_openai_client, test_config):
        """Test creating Inquiry from CSV file with array types."""
        # Create temporary CSV file with array types
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            tmp.write("question,field_name,data_type\n")
            tmp.write("\"Who are the authors?\",authors,list(str)\n")
            tmp.write("\"What are the keywords?\",keywords,list(str)\n")
            tmp.write("\"What is the title?\",title,str\n")
            tmp_path = tmp.name
        
        try:
            inquiry = Inquiry.from_file(tmp_path, client=mock_openai_client, config=test_config)
            
            assert len(inquiry.questions) == 3
            assert inquiry.questions["authors"]["type"] == "list(str)"
            assert inquiry.questions["keywords"]["type"] == "list(str)"
            assert inquiry.questions["title"]["type"] == "str"
            
        finally:
            os.unlink(tmp_path)


class TestArrayDateTimeTypes:
    """Test suite for array types with date/datetime elements."""
    
    def test_array_date_types(self):
        """Test array types with date elements."""
        questions = {
            "publication_dates": {
                "question": "What are the publication dates?",
                "type": "list(date)",
                "output_name": "publication_dates"
            }
        }
        
        schema = build_schema_from_questions(questions)
        
        # Verify schema was created
        assert schema is not None
        assert 'publication_dates' in schema.model_fields
    
    def test_array_datetime_types(self):
        """Test array types with datetime elements."""
        questions = {
            "timestamps": {
                "question": "What are the timestamps?",
                "type": "list(datetime)",
                "output_name": "timestamps"
            }
        }
        
        schema = build_schema_from_questions(questions)
        
        # Verify schema was created
        assert schema is not None
        assert 'timestamps' in schema.model_fields
