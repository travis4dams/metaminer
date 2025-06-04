"""
Test cases for enum handling with default values and flexible validation.
"""
import pytest
import tempfile
import os
from metaminer.question_parser import parse_questions_from_file, _validate_default_value
from metaminer.schema_builder import build_schema_from_questions, validate_extraction_result
from metaminer.inquiry import Inquiry
from unittest.mock import MagicMock


class TestEnumDefaultValues:
    """Test enum fields with default values."""
    
    def test_validate_enum_default_values(self):
        """Test validation of enum default values."""
        # Valid enum default
        result = _validate_default_value("dovish", "enum(dovish,neutral,hawkish)", "test_field")
        assert result == "dovish"
        
        # Invalid enum default should raise error
        with pytest.raises(ValueError, match="not in enum values"):
            _validate_default_value("invalid", "enum(dovish,neutral,hawkish)", "test_field")
        
        # Multi-enum default
        result = _validate_default_value("dovish,neutral", "multi_enum(dovish,neutral,hawkish)", "test_field")
        assert result == ["dovish", "neutral"]
        
        # Invalid multi-enum default
        with pytest.raises(ValueError, match="not in enum values"):
            _validate_default_value("dovish,invalid", "multi_enum(dovish,neutral,hawkish)", "test_field")
    
    def test_validate_other_default_values(self):
        """Test validation of non-enum default values."""
        # String
        assert _validate_default_value("test", "str", "field") == "test"
        
        # Integer
        assert _validate_default_value("42", "int", "field") == 42
        
        # Float
        assert _validate_default_value("3.14", "float", "field") == 3.14
        
        # Boolean
        assert _validate_default_value("true", "bool", "field") is True
        assert _validate_default_value("false", "bool", "field") is False
        assert _validate_default_value("1", "bool", "field") is True
        assert _validate_default_value("0", "bool", "field") is False
        
        # Date
        result = _validate_default_value("2024-01-01", "date", "field")
        assert result == "2024-01-01"  # Should remain as string for schema builder
    
    def test_csv_parsing_with_defaults(self):
        """Test CSV parsing with default values."""
        csv_content = '''question,field_name,data_type,default_value
"What is the sentiment?",sentiment,"enum(dovish,neutral,hawkish)",neutral
"What is the title?",title,str,"Untitled Document"
"How many pages?",page_count,int,1
"Is it published?",published,bool,false
'''
        
        # Use delete=False and manually handle cleanup for Windows compatibility
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        try:
            temp_file.write(csv_content)
            temp_file.flush()
            temp_file.close()  # Explicitly close the file before reading
            
            questions = parse_questions_from_file(temp_file.name)
            
            # Check that defaults were parsed and validated correctly
            assert questions["sentiment"]["default"] == "neutral"
            assert questions["title"]["default"] == "Untitled Document"
            assert questions["page_count"]["default"] == 1
            assert questions["published"]["default"] is False
            
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_file.name)
            except (OSError, PermissionError):
                # On Windows, sometimes the file is still locked
                # Try again after a brief moment or ignore if it fails
                import time
                time.sleep(0.1)
                try:
                    os.unlink(temp_file.name)
                except (OSError, PermissionError):
                    pass  # Ignore cleanup failures in tests
    
    def test_schema_with_enum_defaults(self):
        """Test schema building with enum defaults."""
        questions = {
            "sentiment": {
                "question": "What is the sentiment?",
                "type": "enum(dovish,neutral,hawkish)",
                "default": "neutral",
                "output_name": "sentiment"
            },
            "title": {
                "question": "What is the title?",
                "type": "str",
                "default": "Untitled",
                "output_name": "title"
            }
        }
        
        schema_class = build_schema_from_questions(questions)
        
        # Test with valid enum value
        valid_data = {"sentiment": "dovish", "title": "Test Title"}
        instance = schema_class(**valid_data)
        assert instance.sentiment == "dovish"
        assert instance.title == "Test Title"
        
        # Test with invalid enum value (should fall back to None due to our validator)
        invalid_data = {"sentiment": "<UNKNOWN>", "title": "Test Title"}
        instance = schema_class(**invalid_data)
        assert instance.sentiment is None  # Our validator converts invalid values to None
        assert instance.title == "Test Title"
        
        # Test with missing values (should use defaults)
        empty_data = {}
        instance = schema_class(**empty_data)
        assert instance.sentiment == "neutral"  # Should use default
        assert instance.title == "Untitled"  # Should use default
    
    def test_enum_validation_with_unknown_values(self):
        """Test that enum validation handles unknown values gracefully."""
        questions = {
            "hawkdove": {
                "question": "What is the hawk/dove stance?",
                "type": "enum(dovish,slightlydovish,neutral,slightlyhawkish,hawkish)",
                "output_name": "hawkdove"
            }
        }
        
        schema_class = build_schema_from_questions(questions)
        
        # Test the original error case
        result_data = {"hawkdove": "<UNKNOWN>"}
        
        # This should NOT raise a ValidationError anymore
        instance = schema_class(**result_data)
        assert instance.hawkdove is None  # Invalid value converted to None
        
        # Test with None directly
        result_data = {"hawkdove": None}
        instance = schema_class(**result_data)
        assert instance.hawkdove is None
        
        # Test with valid value
        result_data = {"hawkdove": "neutral"}
        instance = schema_class(**result_data)
        assert instance.hawkdove == "neutral"
    
    def test_multi_enum_validation(self):
        """Test multi-enum validation with invalid values."""
        questions = {
            "topics": {
                "question": "What topics are covered?",
                "type": "multi_enum(finance,hr,marketing)",
                "output_name": "topics"
            }
        }
        
        schema_class = build_schema_from_questions(questions)
        
        # Valid multi-enum
        result_data = {"topics": ["finance", "hr"]}
        instance = schema_class(**result_data)
        assert instance.topics == ["finance", "hr"]
        
        # Mixed valid/invalid values (should filter out invalid ones)
        result_data = {"topics": ["finance", "invalid", "hr"]}
        instance = schema_class(**result_data)
        assert instance.topics == ["finance", "hr"]  # Invalid value filtered out
        
        # All invalid values
        result_data = {"topics": ["invalid1", "invalid2"]}
        instance = schema_class(**result_data)
        assert instance.topics is None  # No valid values, return None
        
        # Invalid format (not a list)
        result_data = {"topics": "finance"}
        instance = schema_class(**result_data)
        assert instance.topics is None  # Invalid format, return None


class TestInquiryWithDefaults:
    """Test Inquiry class with default values."""
    
    def test_inquiry_with_enum_defaults(self):
        """Test Inquiry creation with enum defaults."""
        questions = {
            "sentiment": {
                "question": "What is the sentiment?",
                "type": "enum(dovish,neutral,hawkish)",
                "default": "neutral"
            }
        }
        
        # Mock OpenAI client
        mock_client = MagicMock()
        
        # Create inquiry
        inquiry = Inquiry(questions=questions, client=mock_client)
        
        # Check that the schema was built correctly
        assert inquiry.schema_class is not None
        assert "sentiment" in inquiry.questions
        assert inquiry.questions["sentiment"]["default"] == "neutral"
    
    def test_extraction_result_validation_with_defaults(self):
        """Test extraction result validation with default fallbacks."""
        questions = {
            "hawkdove": {
                "question": "What is the hawk/dove stance?",
                "type": "enum(dovish,slightlydovish,neutral,slightlyhawkish,hawkish)",
                "default": "neutral",
                "output_name": "hawkdove"
            }
        }
        
        schema_class = build_schema_from_questions(questions)
        
        # Test the original problematic case
        result_dict = {"hawkdove": "<UNKNOWN>"}
        
        # This should work now without raising ValidationError
        validated_result = validate_extraction_result(result_dict, schema_class)
        assert validated_result.hawkdove is None  # Invalid value becomes None
        
        # Test with payload structure (like in the original error)
        result_dict = {"payload": {"hawkdove": "<UNKNOWN>"}}
        
        # This would fail because the schema expects "hawkdove" at top level, not in "payload"
        # The schema will use the default value since hawkdove is missing
        validated_result = validate_extraction_result(result_dict, schema_class)
        assert validated_result.hawkdove == "neutral"  # Should use default value


if __name__ == "__main__":
    pytest.main([__file__])
