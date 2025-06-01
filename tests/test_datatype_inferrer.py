"""
Tests for the DataTypeInferrer module.
"""

import pytest
from unittest.mock import Mock, patch
import openai
from pydantic import ValidationError

from metaminer.datatype_inferrer import (
    DataTypeInferrer, 
    TypeSuggestion, 
    InferenceResponse,
    infer_question_types,
    _is_metaminer_type_valid
)
from metaminer.config import Config


class TestTypeSuggestion:
    """Test the TypeSuggestion Pydantic model."""
    
    def test_valid_type_suggestion(self):
        """Test creating a valid TypeSuggestion."""
        suggestion = TypeSuggestion(
            suggested_type="str",
            reasoning="Default text type",
            alternatives=["int", "bool"]
        )
        
        assert suggestion.suggested_type == "str"
        assert suggestion.reasoning == "Default text type"
        assert suggestion.alternatives == ["int", "bool"]
    
    def test_invalid_suggested_type(self):
        """Test that invalid suggested types are rejected."""
        with pytest.raises(ValidationError):
            TypeSuggestion(
                suggested_type="invalid_type",
                reasoning="Test",
                alternatives=[]
            )
    
    def test_invalid_alternative_type(self):
        """Test that invalid alternative types are rejected."""
        with pytest.raises(ValidationError):
            TypeSuggestion(
                suggested_type="str",
                reasoning="Test",
                alternatives=["invalid_type"]
            )
    
    def test_enum_type_suggestion(self):
        """Test creating a TypeSuggestion with enum type."""
        suggestion = TypeSuggestion(
            suggested_type="enum(low,medium,high)",
            reasoning="Priority level question",
            alternatives=["str"]
        )
        
        assert suggestion.suggested_type == "enum(low,medium,high)"
        assert "Priority level" in suggestion.reasoning
    
    def test_array_type_suggestion(self):
        """Test creating a TypeSuggestion with array type."""
        suggestion = TypeSuggestion(
            suggested_type="list(str)",
            reasoning="Multiple values expected",
            alternatives=["str"]
        )
        
        assert suggestion.suggested_type == "list(str)"


class TestInferenceResponse:
    """Test the InferenceResponse Pydantic model."""
    
    def test_valid_inference_response(self):
        """Test creating a valid InferenceResponse."""
        response_data = {
            "suggestions": {
                "question1": {
                    "suggested_type": "str",
                    "reasoning": "Default type",
                    "alternatives": ["int"]
                }
            }
        }
        
        response = InferenceResponse(**response_data)
        assert "question1" in response.suggestions
    
    def test_missing_required_fields(self):
        """Test that missing required fields are rejected."""
        response_data = {
            "suggestions": {
                "question1": {
                    "suggested_type": "str"
                    # Missing 'reasoning' field
                }
            }
        }
        
        with pytest.raises(ValidationError):
            InferenceResponse(**response_data)


class TestMetaminerTypeValidation:
    """Test the _is_metaminer_type_valid function."""
    
    def test_basic_types(self):
        """Test validation of basic types."""
        basic_types = ["str", "int", "float", "bool", "date", "datetime"]
        for type_str in basic_types:
            assert _is_metaminer_type_valid(type_str)
    
    def test_array_types(self):
        """Test validation of array types."""
        array_types = ["list(str)", "list(int)", "list(float)", "list(bool)", "list(date)", "list(datetime)"]
        for type_str in array_types:
            assert _is_metaminer_type_valid(type_str)
    
    def test_enum_types(self):
        """Test validation of enum types."""
        enum_types = [
            "enum(low,medium,high)",
            "multi_enum(finance,hr,marketing)",
            "enum(yes,no)"
        ]
        for type_str in enum_types:
            assert _is_metaminer_type_valid(type_str)
    
    def test_invalid_types(self):
        """Test that invalid types are rejected."""
        invalid_types = [
            "invalid_type",
            "list(invalid)",
            "enum()",
            "multi_enum()",
            "dict",
            "tuple"
        ]
        for type_str in invalid_types:
            assert not _is_metaminer_type_valid(type_str)


class TestDataTypeInferrer:
    """Test the DataTypeInferrer class."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenAI client."""
        client = Mock(spec=openai.OpenAI)
        
        # Mock models.list()
        models_mock = Mock()
        models_mock.data = [Mock(id="gpt-3.5-turbo")]
        client.models.list.return_value = models_mock
        
        return client
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = Config()
        # Override values for testing
        config.api_key = "test-key"
        config.base_url = "http://localhost:8000"
        config.timeout = 30
        config.max_retries = 3
        return config
    
    def test_init_with_client(self, mock_client, config):
        """Test initializing DataTypeInferrer with provided client."""
        inferrer = DataTypeInferrer(client=mock_client, config=config)
        assert inferrer.client == mock_client
        assert inferrer.config == config
    
    def test_init_without_client(self, config):
        """Test initializing DataTypeInferrer without client."""
        with patch('metaminer.datatype_inferrer.openai.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            inferrer = DataTypeInferrer(config=config)
            assert inferrer.client is not None
            mock_openai.assert_called_once()
    
    def test_get_available_types(self, mock_client, config):
        """Test getting available types."""
        inferrer = DataTypeInferrer(client=mock_client, config=config)
        types = inferrer._get_available_types()
        
        # Check that basic types are included
        assert "str" in types
        assert "int" in types
        assert "date" in types
        
        # Check that array types are included
        assert "list(str)" in types
        assert "list(int)" in types
        
        # Check that enum examples are included
        assert any("enum(" in t for t in types)
        assert any("multi_enum(" in t for t in types)
    
    def test_create_inference_prompt(self, mock_client, config):
        """Test creating inference prompt."""
        inferrer = DataTypeInferrer(client=mock_client, config=config)
        questions = {
            "question1": "What is the date?",
            "question2": "How many items?"
        }
        
        prompt = inferrer._create_inference_prompt(questions)
        
        assert "What is the date?" in prompt
        assert "How many items?" in prompt
        assert "metaminer system" in prompt
        assert "JSON object" in prompt
    
    def test_fallback_suggestions(self, mock_client, config):
        """Test creating fallback suggestions."""
        inferrer = DataTypeInferrer(client=mock_client, config=config)
        questions = {
            "date_question": "What is the date?",
            "count_question": "How many items?",
            "bool_question": "Is this correct?",
            "priority_question": "What is the priority level?",
            "general_question": "What is the title?"
        }
        
        suggestions = inferrer._create_fallback_suggestions(questions)
        
        assert suggestions["date_question"].suggested_type == "date"
        assert suggestions["count_question"].suggested_type == "int"
        assert suggestions["bool_question"].suggested_type == "bool"
        assert suggestions["priority_question"].suggested_type == "enum(low,medium,high)"
        assert suggestions["general_question"].suggested_type == "str"
    
    def test_infer_types_with_list_input(self, mock_client, config):
        """Test inferring types with list input."""
        inferrer = DataTypeInferrer(client=mock_client, config=config)
        
        # Mock API response
        mock_response = Mock()
        mock_response.suggestions = {
            "question_1": {
                "suggested_type": "date",
                "reasoning": "Asks for a date",
                "alternatives": ["str"]
            }
        }
        
        with patch.object(inferrer, '_call_openai_api', return_value=mock_response):
            questions = ["What is the date?"]
            suggestions = inferrer.infer_types(questions)
            
            assert "question_1" in suggestions
            assert suggestions["question_1"].suggested_type == "date"
    
    def test_infer_types_with_dict_input(self, mock_client, config):
        """Test inferring types with dictionary input."""
        inferrer = DataTypeInferrer(client=mock_client, config=config)
        
        # Mock API response
        mock_response = Mock()
        mock_response.suggestions = {
            "date_field": {
                "suggested_type": "date",
                "reasoning": "Asks for a date",
                "alternatives": ["str"]
            }
        }
        
        with patch.object(inferrer, '_call_openai_api', return_value=mock_response):
            questions = {"date_field": "What is the date?"}
            suggestions = inferrer.infer_types(questions)
            
            assert "date_field" in suggestions
            assert suggestions["date_field"].suggested_type == "date"
    
    def test_infer_single_type(self, mock_client, config):
        """Test inferring type for a single question."""
        inferrer = DataTypeInferrer(client=mock_client, config=config)
        
        # Mock API response
        mock_response = Mock()
        mock_response.suggestions = {
            "question": {
                "suggested_type": "int",
                "reasoning": "Asks for a count",
                "alternatives": ["str"]
            }
        }
        
        with patch.object(inferrer, '_call_openai_api', return_value=mock_response):
            suggestion = inferrer.infer_single_type("How many items?")
            
            assert suggestion.suggested_type == "int"
            assert "count" in suggestion.reasoning
    
    def test_api_failure_fallback(self, mock_client, config):
        """Test that fallback suggestions are used when API fails."""
        inferrer = DataTypeInferrer(client=mock_client, config=config)
        
        with patch.object(inferrer, '_call_openai_api', side_effect=Exception("API Error")):
            questions = {"date_question": "What is the date?"}
            suggestions = inferrer.infer_types(questions)
            
            # Should get fallback suggestion
            assert "date_question" in suggestions
            assert suggestions["date_question"].suggested_type == "date"
    
    def test_invalid_suggested_type_handling(self, mock_client, config):
        """Test handling of invalid suggested types from API."""
        inferrer = DataTypeInferrer(client=mock_client, config=config)
        
        # Mock API response with invalid type
        mock_response = Mock()
        mock_response.suggestions = {
            "question1": {
                "suggested_type": "invalid_type",
                "reasoning": "Test",
                "alternatives": ["str"]
            }
        }
        
        with patch.object(inferrer, '_call_openai_api', return_value=mock_response):
            questions = {"question1": "What is this?"}
            suggestions = inferrer.infer_types(questions)
            
            # Should fallback to 'str' for invalid type
            assert suggestions["question1"].suggested_type == "str"


class TestConvenienceFunction:
    """Test the convenience function."""
    
    def test_infer_question_types_function(self):
        """Test the convenience function."""
        questions = ["What is the date?"]
        
        with patch('metaminer.datatype_inferrer.DataTypeInferrer') as mock_inferrer_class:
            mock_inferrer = Mock()
            mock_inferrer.infer_types.return_value = {
                "question_1": TypeSuggestion(
                    suggested_type="date",
                    reasoning="Date question",
                    alternatives=["str"]
                )
            }
            mock_inferrer_class.return_value = mock_inferrer
            
            result = infer_question_types(questions)
            
            mock_inferrer_class.assert_called_once()
            mock_inferrer.infer_types.assert_called_once_with(questions)
            assert "question_1" in result


class TestIntegration:
    """Integration tests for DataTypeInferrer."""
    
    def test_real_api_structure(self):
        """Test with realistic API response structure."""
        # This test uses mocked responses but with realistic structure
        mock_client = Mock(spec=openai.OpenAI)
        
        # Mock models.list()
        models_mock = Mock()
        models_mock.data = [Mock(id="gpt-3.5-turbo")]
        mock_client.models.list.return_value = models_mock
        
        # Mock structured output response
        mock_parsed_response = InferenceResponse(
            suggestions={
                "doc_date": {
                    "suggested_type": "date",
                    "reasoning": "Question asks for a document date",
                    "alternatives": ["str", "datetime"]
                },
                "priority": {
                    "suggested_type": "enum(low,medium,high,urgent)",
                    "reasoning": "Priority suggests categorical values",
                    "alternatives": ["str"]
                },
                "page_count": {
                    "suggested_type": "int",
                    "reasoning": "Asks for a count of pages",
                    "alternatives": ["str"]
                }
            }
        )
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = mock_parsed_response
        
        mock_client.beta.chat.completions.parse.return_value = mock_response
        
        config = Config()
        config.api_key = "test-key"
        inferrer = DataTypeInferrer(client=mock_client, config=config)
        
        questions = {
            "doc_date": "What is the document date?",
            "priority": "What is the priority level?",
            "page_count": "How many pages are there?"
        }
        
        suggestions = inferrer.infer_types(questions)
        
        assert len(suggestions) == 3
        assert suggestions["doc_date"].suggested_type == "date"
        assert suggestions["priority"].suggested_type == "enum(low,medium,high,urgent)"
        assert suggestions["page_count"].suggested_type == "int"
        
        # Verify all suggestions have proper structure
        for suggestion in suggestions.values():
            assert isinstance(suggestion, TypeSuggestion)
            assert suggestion.suggested_type
            assert suggestion.reasoning
            assert isinstance(suggestion.alternatives, list)
