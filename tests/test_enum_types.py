"""
Test cases for enum type functionality.
"""
import pytest
from typing import get_origin, get_args
from metaminer.question_parser import (
    parse_questions_from_file, 
    _is_valid_enum_type, 
    _extract_enum_values,
    _validate_enum_values
)
from metaminer.schema_builder import (
    build_schema_from_questions,
    _parse_enum_type,
    _get_python_type,
    create_extraction_prompt
)


class TestEnumParsing:
    """Test enum type parsing functionality."""
    
    def test_is_valid_enum_type(self):
        """Test enum type validation."""
        # Valid enum types
        assert _is_valid_enum_type("enum(val1,val2,val3)")
        assert _is_valid_enum_type("multi_enum(a,b,c)")
        assert _is_valid_enum_type("enum(single)")
        assert _is_valid_enum_type("ENUM(VAL1,VAL2)")  # case insensitive
        
        # Invalid enum types
        assert not _is_valid_enum_type("enum()")  # empty
        assert not _is_valid_enum_type("enum")  # no parentheses
        assert not _is_valid_enum_type("str")  # not enum
        assert not _is_valid_enum_type("list(str)")  # array type
    
    def test_validate_enum_values(self):
        """Test enum values validation."""
        # Valid values
        assert _validate_enum_values("val1,val2,val3")
        assert _validate_enum_values("single")
        assert _validate_enum_values("a, b, c")  # with spaces
        
        # Invalid values
        assert not _validate_enum_values("")  # empty
        assert not _validate_enum_values("  ")  # whitespace only
        assert not _validate_enum_values(",")  # empty values
    
    def test_extract_enum_values(self):
        """Test enum values extraction."""
        # Single enum
        values = _extract_enum_values("enum(val1,val2,val3)")
        assert values == ["val1", "val2", "val3"]
        
        # Multi enum
        values = _extract_enum_values("multi_enum(a,b,c)")
        assert values == ["a", "b", "c"]
        
        # With spaces
        values = _extract_enum_values("enum(val1, val2, val3)")
        assert values == ["val1", "val2", "val3"]
        
        # Single value
        values = _extract_enum_values("enum(single)")
        assert values == ["single"]
        
        # Invalid type
        values = _extract_enum_values("str")
        assert values == []
    
    def test_parse_enum_type(self):
        """Test enum type parsing."""
        # Single enum
        is_enum, is_multi, values = _parse_enum_type("enum(val1,val2,val3)")
        assert is_enum is True
        assert is_multi is False
        assert values == ["val1", "val2", "val3"]
        
        # Multi enum
        is_enum, is_multi, values = _parse_enum_type("multi_enum(a,b,c)")
        assert is_enum is True
        assert is_multi is True
        assert values == ["a", "b", "c"]
        
        # Not enum
        is_enum, is_multi, values = _parse_enum_type("str")
        assert is_enum is False
        assert is_multi is False
        assert values == []


class TestEnumSchemaBuilding:
    """Test enum schema building functionality."""
    
    def test_get_python_type_single_enum(self):
        """Test Python type generation for single enum."""
        enum_type = _get_python_type("enum(val1,val2,val3)")
        
        # Should be a Literal type
        assert hasattr(enum_type, '__origin__')
        # The exact structure depends on Python version, but it should contain our values
        
    def test_get_python_type_multi_enum(self):
        """Test Python type generation for multi enum."""
        enum_type = _get_python_type("multi_enum(val1,val2,val3)")
        
        # Should be List[Literal[...]]
        assert get_origin(enum_type) is list
        
    def test_build_schema_with_enums(self):
        """Test schema building with enum fields."""
        questions = {
            "doc_type": {
                "question": "What is the document type?",
                "type": "enum(report,memo,letter)",
                "output_name": "doc_type"
            },
            "topics": {
                "question": "What topics are covered?",
                "type": "multi_enum(finance,hr,marketing)",
                "output_name": "topics"
            },
            "title": {
                "question": "What is the title?",
                "type": "str",
                "output_name": "title"
            }
        }
        
        schema_class = build_schema_from_questions(questions)
        
        # Should create a valid Pydantic model
        assert hasattr(schema_class, 'model_fields')
        assert 'doc_type' in schema_class.model_fields
        assert 'topics' in schema_class.model_fields
        assert 'title' in schema_class.model_fields


class TestEnumPromptGeneration:
    """Test enum prompt generation."""
    
    def test_create_extraction_prompt_with_enums(self):
        """Test prompt generation with enum fields."""
        questions = {
            "doc_type": {
                "question": "What is the document type?",
                "type": "enum(report,memo,letter)",
                "output_name": "doc_type"
            },
            "topics": {
                "question": "What topics are covered?",
                "type": "multi_enum(finance,hr,marketing)",
                "output_name": "topics"
            },
            "title": {
                "question": "What is the title?",
                "type": "str",
                "output_name": "title"
            }
        }
        
        schema_class = build_schema_from_questions(questions)
        prompt = create_extraction_prompt(questions, "Sample document text", schema_class)
        
        # Should contain enum instructions
        assert "Choose one from: [report, memo, letter]" in prompt
        assert "Select all that apply from: [finance, hr, marketing]" in prompt
        assert "title (str):" in prompt  # Regular field format
        assert "For enum fields, you must choose only from the specified valid options" in prompt


class TestEnumCSVParsing:
    """Test CSV parsing with enum types."""
    
    def test_parse_enum_csv_file(self, tmp_path):
        """Test parsing CSV file with enum types."""
        # Create temporary CSV file with properly quoted enum values
        csv_content = '''question,field_name,data_type
"What is the document type?",doc_type,"enum(report,memo,letter)"
"What topics are covered?",topics,"multi_enum(finance,hr,marketing)"
"What is the title?",title,str
'''
        csv_file = tmp_path / "test_enums.csv"
        csv_file.write_text(csv_content)
        
        # Parse the file
        questions = parse_questions_from_file(str(csv_file))
        
        # Verify parsing
        assert len(questions) == 3
        assert questions["doc_type"]["type"] == "enum(report,memo,letter)"
        assert questions["topics"]["type"] == "multi_enum(finance,hr,marketing)"
        assert questions["title"]["type"] == "str"


class TestEnumValidation:
    """Test enum validation functionality."""
    
    def test_enum_validation_success(self):
        """Test successful enum validation."""
        questions = {
            "doc_type": {
                "question": "What is the document type?",
                "type": "enum(report,memo,letter)",
                "output_name": "doc_type"
            }
        }
        
        schema_class = build_schema_from_questions(questions)
        
        # Valid data should pass
        valid_data = {"doc_type": "report"}
        instance = schema_class(**valid_data)
        assert instance.doc_type == "report"
    
    def test_enum_validation_failure(self):
        """Test enum validation failure."""
        questions = {
            "doc_type": {
                "question": "What is the document type?",
                "type": "enum(report,memo,letter)",
                "output_name": "doc_type"
            }
        }
        
        schema_class = build_schema_from_questions(questions)
        
        # Invalid data should fail
        with pytest.raises(Exception):  # Pydantic validation error
            invalid_data = {"doc_type": "invalid_type"}
            schema_class(**invalid_data)


if __name__ == "__main__":
    pytest.main([__file__])
