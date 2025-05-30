"""
Test cases to verify the metaminer fix is working correctly.
"""

import pytest
from metaminer.inquiry import Inquiry
from metaminer.schema_builder import validate_extraction_result, build_schema_from_questions


def test_list_error_handling():
    """Test that we get a clear error message when a list is passed instead of dict."""
    
    # Create a simple schema
    questions = {
        "test_field": {
            "question": "What is the test value?",
            "type": "str",
            "output_name": "test_field"
        }
    }
    
    schema_class = build_schema_from_questions(questions)
    
    # Test with a list (this should fail with a clear error message)
    with pytest.raises(ValueError) as exc_info:
        validate_extraction_result(["item1", "item2"], schema_class)
    
    error_message = str(exc_info.value)
    assert "Expected dictionary for extraction result, got list" in error_message
    assert "This usually indicates the API returned an unexpected format" in error_message


def test_dict_validation_success():
    """Test that correct dict input works properly."""
    
    # Create a simple schema
    questions = {
        "test_field": {
            "question": "What is the test value?",
            "type": "str",
            "output_name": "test_field"
        }
    }
    
    schema_class = build_schema_from_questions(questions)
    
    # Test with correct dict (this should work)
    result = validate_extraction_result({"test_field": "test_value"}, schema_class)
    assert result.test_field == "test_value"


def test_inquiry_creation():
    """Test basic Inquiry functionality."""
    from metaminer.config import Config
    from unittest.mock import MagicMock
    
    # Create test config with API key
    config = Config()
    config.api_key = "test-key"
    
    # Mock OpenAI client
    mock_client = MagicMock()
    
    # Test with simple questions
    inquiry = Inquiry(questions=["What is the title?", "Who is the author?"], client=mock_client, config=config)
    assert len(inquiry.questions) == 2
    assert inquiry.schema_class is not None
    
    # Check that questions were normalized correctly
    assert "question_1" in inquiry.questions
    assert "question_2" in inquiry.questions
    assert inquiry.questions["question_1"]["question"] == "What is the title?"
    assert inquiry.questions["question_2"]["question"] == "Who is the author?"


def test_inquiry_from_dict():
    """Test Inquiry creation from dictionary format."""
    from metaminer.config import Config
    from unittest.mock import MagicMock
    
    # Create test config with API key
    config = Config()
    config.api_key = "test-key"
    
    # Mock OpenAI client
    mock_client = MagicMock()
    
    questions = {
        "title": {
            "question": "What is the title?",
            "type": "str"
        },
        "author": {
            "question": "Who is the author?", 
            "type": "str"
        }
    }
    
    inquiry = Inquiry(questions=questions, client=mock_client, config=config)
    assert len(inquiry.questions) == 2
    assert inquiry.schema_class is not None
    assert "title" in inquiry.questions
    assert "author" in inquiry.questions


def test_schema_building():
    """Test that schema building works correctly with different types."""
    
    questions = {
        "title": {"question": "What is the title?", "type": "str"},
        "page_count": {"question": "How many pages?", "type": "int"},
        "pub_date": {"question": "When was it published?", "type": "date"},
        "is_published": {"question": "Is it published?", "type": "bool"}
    }
    
    schema_class = build_schema_from_questions(questions)
    
    # Test that we can create an instance with the correct types
    instance = schema_class(
        title="Test Title",
        page_count=100,
        pub_date="2024-01-01",
        is_published=True
    )
    
    assert instance.title == "Test Title"
    assert instance.page_count == 100
    assert instance.is_published is True


def test_flexible_date_parsing_original_issue():
    """Test that the original issue with date parsing is resolved."""
    from datetime import date
    
    # This test demonstrates the original issue is fixed:
    # Date fields can now handle human-readable formats like "October 20, 2015"
    questions = {
        "pub_date": {
            "question": "What is the publication date?",
            "type": "date",
            "output_name": "pub_date"
        }
    }
    
    schema_class = build_schema_from_questions(questions)
    
    # This would previously fail with "Input should be a valid date or datetime"
    # Now it should work with flexible parsing
    result_data = {"pub_date": "October 20, 2015"}
    result = validate_extraction_result(result_data, schema_class)
    
    assert result.pub_date == date(2015, 10, 20)
    assert isinstance(result.pub_date, date)


def test_datetime_vs_date_distinction():
    """Test that datetime and date types are properly distinguished."""
    from datetime import date, datetime
    
    questions = {
        "pub_date": {
            "question": "What is the publication date?",
            "type": "date",
            "output_name": "pub_date"
        },
        "created_at": {
            "question": "When was it created?",
            "type": "datetime",
            "output_name": "created_at"
        }
    }
    
    schema_class = build_schema_from_questions(questions)
    
    # Test that both types work with the same input format
    result_data = {
        "pub_date": "October 20, 2015 3:30 PM",
        "created_at": "October 20, 2015 3:30 PM"
    }
    
    result = validate_extraction_result(result_data, schema_class)
    
    # Date field should strip time information
    assert result.pub_date == date(2015, 10, 20)
    assert isinstance(result.pub_date, date)
    assert not isinstance(result.pub_date, datetime)
    
    # Datetime field should preserve time information
    assert isinstance(result.created_at, datetime)
    assert result.created_at.year == 2015
    assert result.created_at.month == 10
    assert result.created_at.day == 20
    assert result.created_at.hour == 15
    assert result.created_at.minute == 30
