"""
Schema builder module for creating dynamic Pydantic models from questions.
"""

from typing import Dict, Any, Type, Optional, List, Tuple, Literal, Union
from functools import lru_cache
import hashlib
import json

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated
from pydantic import BaseModel, Field, field_validator, create_model, BeforeValidator, TypeAdapter
from dateutil import parser as date_parser
from datetime import date, datetime
from .question_parser import _extract_enum_values


# Module-level cached validators for better performance
@lru_cache(maxsize=32)
def get_date_validator(field_name: str):
    """Get a cached date validator function."""
    def validate_date(v):
        if v is None:
            return v
        if isinstance(v, date) and not isinstance(v, datetime):
            return v
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, str):
            try:
                parsed = date_parser.parse(v)
                return parsed.date()
            except (ValueError, TypeError) as e:
                raise ValueError(f"Could not parse date '{v}' for field {field_name}: {e}")
        raise ValueError(f"Invalid date format for field {field_name}: {v}")
    return validate_date


@lru_cache(maxsize=32)
def get_datetime_validator(field_name: str):
    """Get a cached datetime validator function."""
    def validate_datetime(v):
        if v is None or isinstance(v, datetime):
            return v
        if isinstance(v, date):
            return datetime.combine(v, datetime.min.time())
        if isinstance(v, str):
            try:
                return date_parser.parse(v)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Could not parse datetime '{v}' for field {field_name}: {e}")
        raise ValueError(f"Invalid datetime format for field {field_name}: {v}")
    return validate_datetime


@lru_cache(maxsize=32)
def get_type_adapter(schema_class: Type[BaseModel]) -> TypeAdapter:
    """Get a cached TypeAdapter for better performance."""
    return TypeAdapter(schema_class)


def _hash_questions(questions: Dict[str, Dict[str, Any]]) -> str:
    """Create a hash of questions dictionary for caching."""
    # Create a consistent string representation for hashing
    normalized = {}
    for key, value in questions.items():
        normalized[key] = {
            'question': value.get('question', ''),
            'type': value.get('type', 'str'),
            'output_name': value.get('output_name', key),
            'default': value.get('default', None)
        }
    
    questions_str = json.dumps(normalized, sort_keys=True)
    return hashlib.md5(questions_str.encode()).hexdigest()


@lru_cache(maxsize=128)
def get_cached_schema(questions_hash: str, schema_name: str, questions_json: str) -> Type[BaseModel]:
    """Get a cached schema or create a new one if not cached."""
    # Reconstruct questions from JSON for processing
    questions = json.loads(questions_json)
    return _create_schema_uncached(questions, schema_name)


def create_safe_literal_type(enum_values: List[str]):
    """Create a Literal type safely without using eval()."""
    if len(enum_values) == 1:
        # For single values, create Literal directly
        value = enum_values[0]
        return Literal[value]
    elif len(enum_values) == 2:
        return Literal[enum_values[0], enum_values[1]]
    elif len(enum_values) == 3:
        return Literal[enum_values[0], enum_values[1], enum_values[2]]
    elif len(enum_values) == 4:
        return Literal[enum_values[0], enum_values[1], enum_values[2], enum_values[3]]
    elif len(enum_values) == 5:
        return Literal[enum_values[0], enum_values[1], enum_values[2], enum_values[3], enum_values[4]]
    else:
        # For more than 5 values, use tuple unpacking
        # This is safer than eval but has a practical limit
        return Literal[tuple(enum_values)]


def create_date_validator(field_name: str, target_type: type):
    """Create a field validator for flexible date/datetime parsing.
    
    Args:
        field_name: Name of the field being validated
        target_type: Either date or datetime class to determine output type
    """
    def validator(cls, v):
        if v is None or isinstance(v, target_type):
            return v
            
        if isinstance(v, (date, datetime)):
            if target_type == date and isinstance(v, datetime):
                return v.date()
            elif target_type == datetime and isinstance(v, date):
                return datetime.combine(v, datetime.min.time())
            return v
            
        if isinstance(v, str):
            try:
                parsed = date_parser.parse(v)
                return parsed.date() if target_type == date else parsed
            except (ValueError, TypeError) as e:
                raise ValueError(f"Could not parse {target_type.__name__} '{v}' for field {field_name}: {e}")
        
        raise ValueError(f"Invalid {target_type.__name__} format for field {field_name}: {v}")
    
    return field_validator(field_name, mode='before')(validator)


def build_schema_from_questions(questions: Dict[str, Dict[str, Any]], 
                               schema_name: str = "DocumentSchema") -> Type[BaseModel]:
    """
    Build a dynamic Pydantic model from questions dictionary with flexible date parsing and default values.
    Uses caching for better performance when the same questions are used repeatedly.
    
    Args:
        questions: Dictionary of questions with type information
        schema_name: Name for the generated schema class
        
    Returns:
        Type[BaseModel]: Dynamic Pydantic model class
    """
    # Create hash for caching
    questions_hash = _hash_questions(questions)
    questions_json = json.dumps(questions, sort_keys=True)
    
    # Try to get cached schema
    return get_cached_schema(questions_hash, schema_name, questions_json)


def _create_schema_uncached(questions: Dict[str, Dict[str, Any]], schema_name: str) -> Type[BaseModel]:
    """
    Create a schema without caching (used internally by cached function).
    
    Args:
        questions: Dictionary of questions with type information
        schema_name: Name for the generated schema class
        
    Returns:
        Type[BaseModel]: Dynamic Pydantic model class
    """
    fields = {}
    
    for field_name, question_data in questions.items():
        field_type_str = question_data.get("type", "str")
        field_description = question_data.get("question", "")
        output_name = question_data.get("output_name", field_name)
        default_value = question_data.get("default", None)
        
        # Check if this is an array type
        is_array, base_type_str = _parse_array_type(field_type_str)
        
        # Create Field with default value if specified, otherwise use None
        field_kwargs = {"description": field_description}
        if default_value is not None:
            field_kwargs["default"] = default_value
        else:
            field_kwargs["default"] = None
        
        if base_type_str == "date":
            # Use cached date validator
            date_validator = get_date_validator(output_name)
            if is_array:
                annotated_type = Annotated[Optional[List[date]], BeforeValidator(lambda v: [date_validator(item) if item is not None else None for item in (v or [])])]
            else:
                annotated_type = Annotated[Optional[date], BeforeValidator(date_validator)]
            fields[output_name] = (annotated_type, Field(**field_kwargs))
            
        elif base_type_str == "datetime":
            # Use cached datetime validator
            datetime_validator = get_datetime_validator(output_name)
            if is_array:
                annotated_type = Annotated[Optional[List[datetime]], BeforeValidator(lambda v: [datetime_validator(item) if item is not None else None for item in (v or [])])]
            else:
                annotated_type = Annotated[Optional[datetime], BeforeValidator(datetime_validator)]
            fields[output_name] = (annotated_type, Field(**field_kwargs))
            
        else:
            field_type = _get_python_type(field_type_str, output_name)
            # Check if this is an enum type - if so, it's already Optional
            is_enum, _, _ = _parse_enum_type(field_type_str)
            if is_enum:
                # Enum types are already Optional due to the validator
                fields[output_name] = (field_type, Field(**field_kwargs))
            else:
                # Make all non-enum fields Optional
                fields[output_name] = (Optional[field_type], Field(**field_kwargs))
    
    # Create the dynamic model
    return create_model(schema_name, **fields)


def _parse_array_type(type_str: str) -> Tuple[bool, str]:
    """
    Parse array type specification like 'list(str)'.
    
    Args:
        type_str: String representation of the type
        
    Returns:
        Tuple[bool, str]: (is_array, base_type_str)
    """
    type_str = type_str.strip().lower()
    
    # Check if this is an array type specification
    if type_str.startswith("list(") and type_str.endswith(")"):
        # Extract the base type from list(base_type)
        base_type = type_str[5:-1].strip()
        return True, base_type
    
    return False, type_str


def _parse_enum_type(type_str: str) -> Tuple[bool, bool, List[str]]:
    """
    Parse enum type specification like 'enum(val1,val2,val3)' or 'multi_enum(val1,val2,val3)'.
    
    Args:
        type_str: String representation of the type
        
    Returns:
        Tuple[bool, bool, List[str]]: (is_enum, is_multi, enum_values)
    """
    type_str = type_str.strip()
    
    if type_str.startswith("enum(") and type_str.endswith(")"):
        enum_values = _extract_enum_values(type_str)
        return True, False, enum_values
    elif type_str.startswith("multi_enum(") and type_str.endswith(")"):
        enum_values = _extract_enum_values(type_str)
        return True, True, enum_values
    
    return False, False, []


def _get_python_type(type_str: str, field_name: str = None) -> Type:
    """
    Convert string type to Python type with flexible enum handling.
    
    Args:
        type_str: String representation of the type
        field_name: Field name for creating custom validators
        
    Returns:
        Type: Corresponding Python type
    """

    # Check if this is an enum type first
    is_enum, is_multi, enum_values = _parse_enum_type(type_str)
    if is_enum:
        # Create a flexible enum validator that handles invalid values
        def create_enum_validator(valid_values: List[str], is_multi_enum: bool, field_name: str):
            def validate_enum(v):
                if v is None:
                    return None
                
                if is_multi_enum:
                    # Multi-enum: expect a list
                    if not isinstance(v, list):
                        return None  # Invalid format, return None
                    
                    result = []
                    for item in v:
                        if item in valid_values:
                            result.append(item)
                        # Skip invalid items, don't add them to result
                    return result if result else None
                else:
                    # Single enum: expect a single value
                    if v in valid_values:
                        return v
                    else:
                        # Invalid enum value, return None
                        return None
            
            return validate_enum
        
        # Create the validator
        enum_validator = create_enum_validator(enum_values, is_multi, field_name or "unknown")
        
        # Use the safe literal type creation function
        literal_type = create_safe_literal_type(enum_values)
        
        if is_multi:
            # Multi-enum: Optional List of Literal values with validator
            return Annotated[Optional[List[literal_type]], BeforeValidator(enum_validator)]
        else:
            # Single enum: Optional Literal type with validator
            return Annotated[Optional[literal_type], BeforeValidator(enum_validator)]
    
    # Check if this is an array type
    is_array, base_type_str = _parse_array_type(type_str)
    
    # Get the base type
    type_mapping = {
        "str": str,
        "string": str,
        "text": str,
        "int": int,
        "integer": int,
        "number": int,
        "float": float,
        "decimal": float,
        "bool": bool,
        "boolean": bool,
        "date": date,
        "datetime": datetime,
    }
    
    base_type = type_mapping.get(base_type_str.lower(), str)
    
    # Return List[base_type] for array types
    if is_array:
        return List[base_type]
    
    return base_type


def create_extraction_prompt(questions: Dict[str, Dict[str, Any]], 
                           document_text: str,
                           schema_class: Type[BaseModel]) -> str:
    """
    Create a prompt for extracting structured data from document text.
    
    Args:
        questions: Dictionary of questions
        document_text: Text content of the document
        schema_class: Pydantic model class for structured output
        
    Returns:
        str: Formatted prompt for the LLM
    """
    # Build questions list
    questions_list = []
    for field_name, question_data in questions.items():
        output_name = question_data.get("output_name", field_name)
        question_text = question_data.get("question", "")
        data_type = question_data.get("type", "str")
        
        # Check if this is an enum type and provide enhanced instructions
        is_enum, is_multi, enum_values = _parse_enum_type(data_type)
        if is_enum:
            values_str = ", ".join(enum_values)
            if is_multi:
                instruction = f"Select all that apply from: [{values_str}]"
                questions_list.append(f"- {output_name}: {question_text}\n  {instruction}")
            else:
                instruction = f"Choose one from: [{values_str}]"
                questions_list.append(f"- {output_name}: {question_text}\n  {instruction}")
        else:
            # Use current format for non-enum types
            questions_list.append(f"- {output_name} ({data_type}): {question_text}")
    
    questions_str = "\n".join(questions_list)
    
    prompt = f"""Please analyze the following document and extract the requested information.

Document text:
{document_text}

Please answer the following questions based on the document content:
{questions_str}

Return your response as a JSON object with the exact field names specified above. If information is not available in the document, use null for the field value.

For enum fields, you must choose only from the specified valid options. If the document contains similar but not exact matches, choose the closest valid option or use null if no reasonable match exists.

Example response format:
{{
    "field_name_1": "extracted_value_1",
    "field_name_2": "extracted_value_2",
    "field_name_3": null
}}
"""
    
    return prompt


def validate_extraction_result(result: Dict[str, Any], 
                             schema_class: Type[BaseModel]) -> BaseModel:
    """
    Validate and parse extraction result using the schema.
    
    Args:
        result: Raw extraction result dictionary
        schema_class: Pydantic model class for validation
        
    Returns:
        BaseModel: Validated model instance
        
    Raises:
        ValueError: If validation fails
    """
    # Check if result is the expected type
    if not isinstance(result, dict):
        result_type = type(result).__name__
        raise ValueError(
            f"Expected dictionary for extraction result, got {result_type}. "
            f"This usually indicates the API returned an unexpected format. "
            f"Result: {result}"
        )
    
    try:
        return schema_class(**result)
    except Exception as e:
        raise ValueError(f"Failed to validate extraction result: {e}")


def schema_to_dict(schema_instance: BaseModel, schema_class: Type[BaseModel] = None) -> Dict[str, Any]:
    """
    Convert schema instance to dictionary.
    
    Args:
        schema_instance: Validated Pydantic model instance
        schema_class: Optional schema class (unused, kept for backward compatibility)
        
    Returns:
        Dict[str, Any]: Dictionary representation
    """
    return schema_instance.model_dump()


def get_schema_fields(schema_class: Type[BaseModel]) -> Dict[str, str]:
    """
    Get field names and types from a schema class.
    
    Args:
        schema_class: Pydantic model class
        
    Returns:
        Dict[str, str]: Mapping of field names to type names
    """
    fields = {}
    for field_name, field_info in schema_class.model_fields.items():
        field_type = field_info.annotation
        if hasattr(field_type, '__name__'):
            type_name = field_type.__name__
        else:
            type_name = str(field_type)
        fields[field_name] = type_name
    
    return fields
