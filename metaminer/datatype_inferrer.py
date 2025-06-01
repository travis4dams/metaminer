"""
Data type inference module for automatically determining appropriate data types for questions.
"""

from typing import Dict, List, Any, Optional, Union, Literal
import openai
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field, field_validator

from .config import Config, setup_logging
from .question_parser import _is_valid_array_type, _is_valid_enum_type


class TypeSuggestion(BaseModel):
    """
    Represents a suggested data type for a question with reasoning.
    """
    suggested_type: str = Field(description="The suggested data type")
    reasoning: str = Field(description="Explanation for why this type was chosen")
    alternatives: List[str] = Field(default_factory=list, description="Alternative type suggestions")
    
    @field_validator('suggested_type')
    @classmethod
    def validate_suggested_type(cls, v):
        """Validate that the suggested type is supported by metaminer."""
        if not _is_metaminer_type_valid(v):
            raise ValueError(f"Invalid metaminer data type: {v}")
        return v
    
    @field_validator('alternatives')
    @classmethod
    def validate_alternatives(cls, v):
        """Validate that alternative types are supported by metaminer."""
        for alt_type in v:
            if not _is_metaminer_type_valid(alt_type):
                raise ValueError(f"Invalid alternative metaminer data type: {alt_type}")
        return v


class InferenceResponse(BaseModel):
    """
    Pydantic model for the API response structure.
    """
    suggestions: Dict[str, Dict[str, Any]] = Field(description="Type suggestions for each question")
    
    @field_validator('suggestions')
    @classmethod
    def validate_suggestions(cls, v):
        """Validate the structure of suggestions."""
        for question_name, suggestion_data in v.items():
            if not isinstance(suggestion_data, dict):
                raise ValueError(f"Suggestion for {question_name} must be a dictionary")
            
            required_fields = ['suggested_type', 'reasoning']
            for field in required_fields:
                if field not in suggestion_data:
                    raise ValueError(f"Missing required field '{field}' for {question_name}")
        
        return v


def _is_metaminer_type_valid(type_str: str) -> bool:
    """
    Validate that a type string is supported by metaminer.
    
    Args:
        type_str: Type string to validate
        
    Returns:
        True if valid, False otherwise
    """
    type_str = type_str.strip()
    
    # Basic types
    basic_types = {"str", "int", "float", "bool", "date", "datetime"}
    if type_str in basic_types:
        return True
    
    # Array types
    if _is_valid_array_type(type_str):
        return True
    
    # Enum types
    if _is_valid_enum_type(type_str):
        return True
    
    return False


class DataTypeInferrer:
    """
    Infers appropriate data types for questions using OpenAI API.
    
    This class analyzes questions without specified data types and suggests
    appropriate metaminer-compatible data types based on question content and context.
    """
    
    def __init__(self, client: openai.OpenAI = None, config: Config = None):
        """
        Initialize the DataTypeInferrer.
        
        Args:
            client: OpenAI client instance
            config: Configuration instance
        """
        # Initialize configuration
        self.config = config or Config()
        self.config.validate()
        
        # Set up logging
        self.logger = setup_logging(self.config)
        
        # Initialize OpenAI client
        if client:
            self.client = client
        else:
            api_base_url = self.config.base_url
            
            client_kwargs = {
                "base_url": api_base_url,
                "timeout": self.config.timeout,
                "max_retries": self.config.max_retries
            }
            
            # Add API key - use dummy key for local APIs if none provided
            api_key = self.config.api_key or "dummy-key-for-local-api"
            client_kwargs["api_key"] = api_key
            
            try:
                self.client = openai.OpenAI(**client_kwargs)
                self.logger.info(f"Initialized OpenAI client for type inference with base URL: {api_base_url}")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}")
                raise RuntimeError(f"Failed to initialize OpenAI client: {e}")
    
    def infer_types(self, questions: Union[List[str], Dict[str, str]]) -> Dict[str, TypeSuggestion]:
        """
        Infer data types for multiple questions.
        
        Args:
            questions: List of question strings or dict mapping names to questions
            
        Returns:
            Dict mapping question identifiers to TypeSuggestion objects
        """
        if isinstance(questions, list):
            # Convert list to dict with generated keys
            questions_dict = {f"question_{i+1}": q for i, q in enumerate(questions)}
        else:
            questions_dict = questions
        
        if not questions_dict:
            return {}
        
        self.logger.info(f"Inferring types for {len(questions_dict)} questions")
        
        # Create inference prompt
        prompt = self._create_inference_prompt(questions_dict)
        
        # Call OpenAI API
        try:
            response = self._call_openai_api(prompt)
            suggestions = self._parse_inference_response(response, questions_dict)
            
            self.logger.info(f"Successfully inferred types for {len(suggestions)} questions")
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to infer types: {e}")
            # Return fallback suggestions
            return self._create_fallback_suggestions(questions_dict)
    
    def infer_single_type(self, question: str, question_name: str = "question") -> TypeSuggestion:
        """
        Infer data type for a single question.
        
        Args:
            question: The question text
            question_name: Optional name for the question
            
        Returns:
            TypeSuggestion object
        """
        results = self.infer_types({question_name: question})
        return results.get(question_name, self._create_fallback_suggestion(question))
    
    def _get_available_types(self) -> List[str]:
        """
        Get list of available data types in metaminer.
        
        Returns:
            List of supported type strings
        """
        basic_types = [
            "str", "int", "float", "bool", "date", "datetime"
        ]
        
        array_types = [
            "list(str)", "list(int)", "list(float)", "list(bool)", 
            "list(date)", "list(datetime)"
        ]
        
        # Note: enum types are dynamic and will be suggested based on context
        enum_examples = [
            "enum(value1,value2,value3)",
            "multi_enum(value1,value2,value3)"
        ]
        
        return basic_types + array_types + enum_examples
    
    def _create_inference_prompt(self, questions: Dict[str, str]) -> str:
        """
        Create a prompt for type inference.
        
        Args:
            questions: Dictionary mapping question names to question text
            
        Returns:
            Formatted prompt string
        """
        available_types = self._get_available_types()
        
        questions_list = []
        for name, text in questions.items():
            questions_list.append(f'"{name}": "{text}"')
        
        questions_str = "{\n  " + ",\n  ".join(questions_list) + "\n}"
        
        prompt = f"""You are a data type inference expert. Analyze the following questions and suggest the most appropriate data types for each one.

Available data types in the metaminer system:
- Basic types: str, int, float, bool, date, datetime
- Array types: list(str), list(int), list(float), list(bool), list(date), list(datetime)
- Enum types: enum(value1,value2,value3) for single selection from predefined values
- Multi-enum types: multi_enum(value1,value2,value3) for multiple selections from predefined values

Questions to analyze:
{questions_str}

For each question, consider:
1. What type of answer is expected (text, number, date, boolean, etc.)?
2. Is this likely to be a single value or multiple values (array)?
3. Are there likely to be predefined categorical options (enum)?
4. What are the most probable enum values if applicable?

Guidelines:
- Use "date" for questions asking for dates without time
- Use "datetime" for questions asking for dates with time
- Use "int" for whole numbers, "float" for decimal numbers
- Use "bool" for yes/no or true/false questions
- Use "enum" when there are likely predefined categorical options
- Use "multi_enum" when multiple categories can be selected
- Use "list(type)" when multiple values of the same type are expected
- Use "str" as fallback for text that doesn't fit other categories

For enum types, suggest realistic values based on the question context.

Return your response as a JSON object with this exact structure:
{{
  "suggestions": {{
    "question_name": {{
      "suggested_type": "type_string",
      "reasoning": "explanation of why this type was chosen",
      "alternatives": ["alternative_type1", "alternative_type2"]
    }}
  }}
}}

Only suggest valid metaminer data types. Provide clear reasoning for each suggestion.
"""
        
        return prompt
    
    def _call_openai_api(self, prompt: str) -> InferenceResponse:
        """
        Call OpenAI API for type inference with structured output.
        
        Args:
            prompt: The inference prompt
            
        Returns:
            Validated InferenceResponse object
        """
        try:
            model_name = self._get_available_model()
            
            # Try structured output first
            try:
                response = self.client.beta.chat.completions.parse(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    response_format=InferenceResponse,
                    temperature=0.1  # Low temperature for consistent results
                )
                result = response.choices[0].message.parsed
                self.logger.debug("Successfully used structured output API for type inference")
                return result
                
            except (AttributeError, Exception) as e:
                self.logger.debug(f"Structured output failed, falling back to JSON mode: {e}")
                
                # Fallback to JSON mode
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                
                result_text = response.choices[0].message.content
                if not result_text:
                    raise ValueError("Empty response from API")
                
                try:
                    result_dict = json.loads(result_text)
                    result = InferenceResponse(**result_dict)
                    self.logger.debug("Successfully used JSON mode API for type inference")
                    return result
                except json.JSONDecodeError as json_e:
                    self.logger.error(f"Failed to parse JSON response: {result_text}")
                    raise ValueError(f"Failed to parse JSON response: {json_e}")
            
        except Exception as e:
            self.logger.error(f"API call failed: {e}")
            raise RuntimeError(f"Failed to call OpenAI API for type inference: {e}")
    
    def _get_available_model(self) -> str:
        """
        Get the first available model from the API.
        
        Returns:
            Model name string
        """
        try:
            models = self.client.models.list()
            if models.data:
                return models.data[0].id
            return "gpt-3.5-turbo"  # fallback
        except Exception:
            return "gpt-3.5-turbo"  # fallback
    
    def _parse_inference_response(self, response: InferenceResponse, 
                                questions: Dict[str, str]) -> Dict[str, TypeSuggestion]:
        """
        Parse the API response into TypeSuggestion objects.
        
        Args:
            response: Validated InferenceResponse object
            questions: Original questions dict for fallback
            
        Returns:
            Dictionary mapping question names to TypeSuggestion objects
        """
        suggestions = {}
        
        for question_name, suggestion_data in response.suggestions.items():
            try:
                # Validate the suggested type
                suggested_type = suggestion_data.get("suggested_type", "str")
                if not _is_metaminer_type_valid(suggested_type):
                    self.logger.warning(f"Invalid suggested type '{suggested_type}' for {question_name}, using 'str'")
                    suggested_type = "str"
                
                # Validate alternatives
                alternatives = []
                for alt_type in suggestion_data.get("alternatives", []):
                    if _is_metaminer_type_valid(alt_type):
                        alternatives.append(alt_type)
                    else:
                        self.logger.warning(f"Invalid alternative type '{alt_type}' for {question_name}, skipping")
                
                suggestion = TypeSuggestion(
                    suggested_type=suggested_type,
                    reasoning=suggestion_data.get("reasoning", "Inferred from question content"),
                    alternatives=alternatives
                )
                
                suggestions[question_name] = suggestion
                
            except Exception as e:
                self.logger.warning(f"Failed to parse suggestion for {question_name}: {e}")
                suggestions[question_name] = self._create_fallback_suggestion(
                    questions.get(question_name, "")
                )
        
        # Ensure all questions have suggestions
        for question_name in questions:
            if question_name not in suggestions:
                suggestions[question_name] = self._create_fallback_suggestion(questions[question_name])
        
        return suggestions
    
    def _create_fallback_suggestions(self, questions: Dict[str, str]) -> Dict[str, TypeSuggestion]:
        """
        Create fallback suggestions when API call fails.
        
        Args:
            questions: Dictionary of questions
            
        Returns:
            Dictionary of fallback TypeSuggestion objects
        """
        suggestions = {}
        for name, question in questions.items():
            suggestions[name] = self._create_fallback_suggestion(question)
        return suggestions
    
    def _create_fallback_suggestion(self, question: str) -> TypeSuggestion:
        """
        Create a fallback suggestion for a single question using simple heuristics.
        
        Args:
            question: Question text
            
        Returns:
            TypeSuggestion with basic heuristics
        """
        question_lower = question.lower()
        
        # Simple heuristics for fallback
        if any(word in question_lower for word in ["date", "when"]) and "time" not in question_lower:
            return TypeSuggestion(
                suggested_type="date",
                reasoning="Contains date-related keywords",
                alternatives=["str", "datetime"]
            )
        
        elif any(word in question_lower for word in ["datetime", "time", "timestamp"]):
            return TypeSuggestion(
                suggested_type="datetime",
                reasoning="Contains time-related keywords",
                alternatives=["str", "date"]
            )
        
        elif any(word in question_lower for word in ["how many", "count", "number", "quantity", "amount"]):
            return TypeSuggestion(
                suggested_type="int",
                reasoning="Asks for quantity or count",
                alternatives=["float", "str"]
            )
        
        elif any(phrase in question_lower for phrase in ["yes or no", "true or false", "is it", "are they", "does it", "did it", "is this", "are these"]):
            return TypeSuggestion(
                suggested_type="bool",
                reasoning="Appears to be yes/no question",
                alternatives=["str"]
            )
        
        elif any(word in question_lower for word in ["priority", "level", "status", "type", "category"]):
            return TypeSuggestion(
                suggested_type="enum(low,medium,high)",
                reasoning="Suggests categorical values",
                alternatives=["str"]
            )
        
        else:
            return TypeSuggestion(
                suggested_type="str",
                reasoning="Default text type",
                alternatives=["int", "bool"]
            )


def infer_question_types(questions: Union[List[str], Dict[str, str]], 
                        client: openai.OpenAI = None,
                        config: Config = None) -> Dict[str, TypeSuggestion]:
    """
    Convenience function to infer types for questions.
    
    Args:
        questions: List of question strings or dict mapping names to questions
        client: Optional OpenAI client
        config: Optional configuration
        
    Returns:
        Dictionary mapping question identifiers to TypeSuggestion objects
    """
    inferrer = DataTypeInferrer(client=client, config=config)
    return inferrer.infer_types(questions)
