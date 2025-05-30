"""
Test cases for flexible date/datetime parsing functionality.
"""

import pytest
from datetime import date, datetime
from metaminer.schema_builder import build_schema_from_questions, validate_extraction_result


def test_date_field_parsing():
    """Test that date fields can parse various date formats."""
    
    questions = {
        "pub_date": {
            "question": "What is the publication date?",
            "type": "date",
            "output_name": "pub_date"
        }
    }
    
    schema_class = build_schema_from_questions(questions)
    
    # Test various date formats
    test_cases = [
        {"pub_date": "October 20, 2015"},
        {"pub_date": "Oct 20, 2015"},
        {"pub_date": "10/20/2015"},
        {"pub_date": "2015-10-20"},
        {"pub_date": "20 Oct 2015"},
        {"pub_date": "2015/10/20"},
    ]
    
    expected_date = date(2015, 10, 20)
    
    for test_data in test_cases:
        result = validate_extraction_result(test_data, schema_class)
        assert result.pub_date == expected_date, f"Failed to parse: {test_data['pub_date']}"


def test_datetime_field_parsing():
    """Test that datetime fields can parse various datetime formats."""
    
    questions = {
        "created_at": {
            "question": "When was it created?",
            "type": "datetime",
            "output_name": "created_at"
        }
    }
    
    schema_class = build_schema_from_questions(questions)
    
    # Test various datetime formats
    test_cases = [
        {"created_at": "October 20, 2015 3:30 PM"},
        {"created_at": "Oct 20, 2015 15:30"},
        {"created_at": "2015-10-20T15:30:00"},
        {"created_at": "2015-10-20 15:30:00"},
        {"created_at": "10/20/2015 3:30 PM"},
    ]
    
    for test_data in test_cases:
        result = validate_extraction_result(test_data, schema_class)
        assert isinstance(result.created_at, datetime), f"Failed to parse datetime: {test_data['created_at']}"
        assert result.created_at.year == 2015
        assert result.created_at.month == 10
        assert result.created_at.day == 20


def test_date_only_from_datetime_string():
    """Test that date fields extract only the date part from datetime strings."""
    
    questions = {
        "pub_date": {
            "question": "What is the publication date?",
            "type": "date",
            "output_name": "pub_date"
        }
    }
    
    schema_class = build_schema_from_questions(questions)
    
    # Test that time information is stripped for date fields
    test_data = {"pub_date": "October 20, 2015 3:30 PM"}
    result = validate_extraction_result(test_data, schema_class)
    
    assert result.pub_date == date(2015, 10, 20)
    assert isinstance(result.pub_date, date)
    assert not isinstance(result.pub_date, datetime)


def test_mixed_date_datetime_schema():
    """Test schema with both date and datetime fields."""
    
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
        },
        "title": {
            "question": "What is the title?",
            "type": "str",
            "output_name": "title"
        }
    }
    
    schema_class = build_schema_from_questions(questions)
    
    test_data = {
        "pub_date": "October 20, 2015",
        "created_at": "October 20, 2015 3:30 PM",
        "title": "Test Document"
    }
    
    result = validate_extraction_result(test_data, schema_class)
    
    assert result.pub_date == date(2015, 10, 20)
    assert isinstance(result.created_at, datetime)
    assert result.created_at.year == 2015
    assert result.created_at.month == 10
    assert result.created_at.day == 20
    assert result.title == "Test Document"


def test_null_date_values():
    """Test that null/None values are handled correctly for date fields."""
    
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
    
    test_data = {
        "pub_date": None,
        "created_at": None
    }
    
    result = validate_extraction_result(test_data, schema_class)
    
    assert result.pub_date is None
    assert result.created_at is None


def test_invalid_date_format_error():
    """Test that invalid date formats produce clear error messages."""
    
    questions = {
        "pub_date": {
            "question": "What is the publication date?",
            "type": "date",
            "output_name": "pub_date"
        }
    }
    
    schema_class = build_schema_from_questions(questions)
    
    test_data = {"pub_date": "not a date"}
    
    with pytest.raises(ValueError) as exc_info:
        validate_extraction_result(test_data, schema_class)
    
    error_message = str(exc_info.value)
    assert "Could not parse date" in error_message
    assert "pub_date" in error_message
    assert "not a date" in error_message


def test_invalid_datetime_format_error():
    """Test that invalid datetime formats produce clear error messages."""
    
    questions = {
        "created_at": {
            "question": "When was it created?",
            "type": "datetime",
            "output_name": "created_at"
        }
    }
    
    schema_class = build_schema_from_questions(questions)
    
    test_data = {"created_at": "invalid datetime"}
    
    with pytest.raises(ValueError) as exc_info:
        validate_extraction_result(test_data, schema_class)
    
    error_message = str(exc_info.value)
    assert "Could not parse datetime" in error_message
    assert "created_at" in error_message
    assert "invalid datetime" in error_message


def test_existing_date_objects():
    """Test that existing date/datetime objects are passed through unchanged."""
    
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
    
    test_date = date(2015, 10, 20)
    test_datetime = datetime(2015, 10, 20, 15, 30)
    
    test_data = {
        "pub_date": test_date,
        "created_at": test_datetime
    }
    
    result = validate_extraction_result(test_data, schema_class)
    
    assert result.pub_date == test_date
    assert result.created_at == test_datetime


def test_cross_type_conversion():
    """Test conversion between date and datetime types."""
    
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
    
    # Test datetime object to date field (should extract date part)
    test_datetime = datetime(2015, 10, 20, 15, 30)
    test_data_1 = {"pub_date": test_datetime, "created_at": None}
    result_1 = validate_extraction_result(test_data_1, schema_class)
    assert result_1.pub_date == date(2015, 10, 20)
    
    # Test date object to datetime field (should add midnight time)
    test_date = date(2015, 10, 20)
    test_data_2 = {"pub_date": None, "created_at": test_date}
    result_2 = validate_extraction_result(test_data_2, schema_class)
    assert result_2.created_at == datetime(2015, 10, 20, 0, 0)


def test_backward_compatibility():
    """Test that existing functionality still works for non-date fields."""
    
    questions = {
        "title": {
            "question": "What is the title?",
            "type": "str",
            "output_name": "title"
        },
        "page_count": {
            "question": "How many pages?",
            "type": "int",
            "output_name": "page_count"
        },
        "is_published": {
            "question": "Is it published?",
            "type": "bool",
            "output_name": "is_published"
        }
    }
    
    schema_class = build_schema_from_questions(questions)
    
    test_data = {
        "title": "Test Document",
        "page_count": 100,
        "is_published": True
    }
    
    result = validate_extraction_result(test_data, schema_class)
    
    assert result.title == "Test Document"
    assert result.page_count == 100
    assert result.is_published is True
