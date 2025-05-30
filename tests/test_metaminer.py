#!/usr/bin/env python3
"""
Pytest test suite for metaminer functionality.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from metaminer import Inquiry
from metaminer.question_parser import parse_questions_from_file
from metaminer.document_reader import extract_text
from metaminer.schema_builder import build_schema_from_questions, create_extraction_prompt


@pytest.fixture
def sample_questions_txt():
    """Sample questions from text file format."""
    return {
        'question_1': {'question': 'What is the document title?', 'type': 'str'},
        'question_2': {'question': 'Who is the author?', 'type': 'str'}
    }


@pytest.fixture
def sample_questions_csv():
    """Sample questions from CSV file format."""
    return {
        'title': {'question': 'What is the document title?', 'type': 'str'},
        'author': {'question': 'Who is the author?', 'type': 'str'},
        'date': {'question': 'When was it written?', 'type': 'date'}
    }


@pytest.fixture
def sample_document_text():
    """Sample document text for testing."""
    return "This is a sample document for testing purposes. It contains some text to extract."


@pytest.fixture
def mock_openai():
    """Mock OpenAI client for testing."""
    with patch('openai.OpenAI') as mock_client:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_client.chat.completions.create.return_value = mock_response
        yield mock_client


class TestQuestionParsing:
    """Test suite for question parsing functionality."""
    
    def test_parse_questions_from_txt_file(self):
        """Test question parsing from text file format."""
        # Check if example file exists before testing
        if os.path.exists('example_questions.txt'):
            questions = parse_questions_from_file('example_questions.txt')
            assert isinstance(questions, dict)
            assert len(questions) > 0
            
            # Verify structure of parsed questions
            for key, value in questions.items():
                assert 'question' in value
                assert isinstance(value['question'], str)
                assert len(value['question']) > 0
    
    def test_parse_questions_from_csv_file(self):
        """Test question parsing from CSV file format."""
        # Check if example file exists before testing
        if os.path.exists('example_questions.csv'):
            questions = parse_questions_from_file('example_questions.csv')
            assert isinstance(questions, dict)
            assert len(questions) > 0
            
            # Verify structure of parsed questions
            for key, value in questions.items():
                assert 'question' in value
                assert 'type' in value
                assert isinstance(value['question'], str)
                assert isinstance(value['type'], str)
                assert len(value['question']) > 0
    
    def test_parse_questions_file_not_found(self):
        """Test error handling when question file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            parse_questions_from_file('nonexistent_file.txt')


class TestDocumentReading:
    """Test suite for document text extraction."""
    
    def test_extract_text_from_file(self):
        """Test document text extraction from file."""
        # Check if example file exists before testing
        if os.path.exists('example_document.txt'):
            text = extract_text('example_document.txt')
            assert isinstance(text, str)
            assert len(text) > 0
    
    def test_extract_text_file_not_found(self):
        """Test error handling when document file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            extract_text('nonexistent_document.txt')
    
    def test_extract_text_returns_string(self, sample_document_text):
        """Test that extracted text is always a string."""
        # This would need to be mocked if testing with actual file operations
        # For now, we'll test the expected behavior
        if os.path.exists('example_document.txt'):
            text = extract_text('example_document.txt')
            assert isinstance(text, str)


class TestSchemaBuilding:
    """Test suite for Pydantic schema generation."""
    
    def test_build_schema_from_questions(self, sample_questions_csv):
        """Test Pydantic schema generation from questions."""
        schema = build_schema_from_questions(sample_questions_csv)
        
        # Verify schema class was created
        assert schema is not None
        assert hasattr(schema, '__name__')
        assert hasattr(schema, 'model_fields')
        
        # Verify fields are present
        assert 'title' in schema.model_fields
        assert 'author' in schema.model_fields
        assert 'date' in schema.model_fields
    
    def test_schema_field_types(self, sample_questions_csv):
        """Test that schema fields have correct types."""
        schema = build_schema_from_questions(sample_questions_csv)
        
        # Check that fields exist
        fields = schema.model_fields
        assert len(fields) == len(sample_questions_csv)
        
        # Verify each field has proper annotation
        for field_name in sample_questions_csv.keys():
            assert field_name in fields
            assert hasattr(fields[field_name], 'annotation')
    
    def test_empty_questions_schema(self):
        """Test schema building with empty questions."""
        schema = build_schema_from_questions({})
        assert schema is not None
        assert len(schema.model_fields) == 0


class TestPromptGeneration:
    """Test suite for LLM prompt generation."""
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'dummy'})
    def test_create_extraction_prompt(self, sample_questions_csv, sample_document_text):
        """Test prompt generation for LLM."""
        schema = build_schema_from_questions(sample_questions_csv)
        prompt = create_extraction_prompt(sample_questions_csv, sample_document_text, schema)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Verify prompt contains key elements
        assert 'title' in prompt.lower()
        assert 'author' in prompt.lower()
        assert sample_document_text in prompt
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'dummy'})
    def test_prompt_with_real_files(self):
        """Test prompt generation with actual example files."""
        if os.path.exists('example_questions.csv') and os.path.exists('example_document.txt'):
            inquiry = Inquiry.from_file('example_questions.csv')
            document_text = extract_text('example_document.txt')
            prompt = create_extraction_prompt(inquiry.questions, document_text, inquiry.schema_class)
            
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            assert document_text in prompt


class TestInquiryIntegration:
    """Test suite for Inquiry class integration."""
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'dummy'})
    def test_inquiry_from_file(self):
        """Test Inquiry creation from file."""
        if os.path.exists('example_questions.csv'):
            inquiry = Inquiry.from_file('example_questions.csv')
            
            assert inquiry is not None
            assert hasattr(inquiry, 'questions')
            assert hasattr(inquiry, 'schema_class')
            assert isinstance(inquiry.questions, dict)
            assert len(inquiry.questions) > 0
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'dummy'})
    def test_inquiry_with_mock_client(self, mock_openai, sample_questions_csv):
        """Test Inquiry with mocked OpenAI client."""
        inquiry = Inquiry(client=mock_openai, questions=sample_questions_csv)
        
        assert inquiry is not None
        assert inquiry.client == mock_openai
        assert len(inquiry.questions) == len(sample_questions_csv)


class TestEndToEndFunctionality:
    """Test suite for end-to-end functionality."""
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'dummy'})
    def test_complete_workflow(self):
        """Test complete workflow with example files."""
        if os.path.exists('example_questions.csv') and os.path.exists('example_document.txt'):
            # Parse questions
            questions = parse_questions_from_file('example_questions.csv')
            assert len(questions) > 0
            
            # Extract document text
            document_text = extract_text('example_document.txt')
            assert len(document_text) > 0
            
            # Build schema
            schema = build_schema_from_questions(questions)
            assert schema is not None
            
            # Generate prompt
            prompt = create_extraction_prompt(questions, document_text, schema)
            assert len(prompt) > 0
            
            # Create inquiry
            inquiry = Inquiry.from_file('example_questions.csv')
            assert inquiry is not None
    
    def test_core_components_available(self):
        """Test that all core components can be imported and instantiated."""
        # Test imports work
        from metaminer import Inquiry
        from metaminer.question_parser import parse_questions_from_file
        from metaminer.document_reader import extract_text
        from metaminer.schema_builder import build_schema_from_questions, create_extraction_prompt
        
        # Test basic functionality without external dependencies
        questions = {
            'test': {'question': 'Test question?', 'type': 'str'}
        }
        schema = build_schema_from_questions(questions)
        assert schema is not None


# Parametrized tests for different file formats
@pytest.mark.parametrize("file_extension,expected_format", [
    ("txt", "text"),
    ("csv", "csv"),
])
def test_question_file_formats(file_extension, expected_format):
    """Test different question file formats."""
    filename = f"example_questions.{file_extension}"
    if os.path.exists(filename):
        questions = parse_questions_from_file(filename)
        assert isinstance(questions, dict)
        
        if expected_format == "csv":
            # CSV format should have type information
            for value in questions.values():
                assert 'type' in value
        elif expected_format == "text":
            # Text format may not have explicit type information
            for value in questions.values():
                assert 'question' in value


# Skip tests if example files are not available
@pytest.mark.skipif(not os.path.exists('tests/example_questions.csv'), 
                   reason="example_questions.csv not found")
def test_csv_file_specific():
    """Test CSV-specific functionality."""
    questions = parse_questions_from_file('tests/example_questions.csv')
    # Verify CSV-specific features
    for value in questions.values():
        assert 'type' in value
        assert value['type'] in ['str', 'int', 'float', 'bool', 'date']


@pytest.mark.skipif(not os.path.exists('tests/example_document.txt'), 
                   reason="example_document.txt not found")
def test_document_file_specific():
    """Test document-specific functionality."""
    text = extract_text('tests/example_document.txt')
    assert len(text) > 50  # Assuming document has substantial content
    assert isinstance(text, str)
