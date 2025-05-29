"""
Schema builder module for creating dynamic Pydantic models from questions.
"""
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel, Field, create_model
from datetime import date, datetime


def build_schema_from_questions(questions: Dict[str, Dict[str, Any]], 
                               schema_name: str = "DocumentSchema") -> Type[BaseModel]:
    """
    Build a dynamic Pydantic model from questions dictionary.
    
    Args:
        questions: Dictionary of questions with type information
        schema_name: Name for the generated schema class
        
    Returns:
        Type[BaseModel]: Dynamic Pydantic model class
    """
    fields = {}
    
    for field_name, question_data in questions.items():
        field_type = _get_python_type(question_data.get("type", "str"))
        field_description = question_data.get("question", "")
        output_name = question_data.get("output_name", field_name)
        
        # Create field with description
        fields[output_name] = (
            field_type, 
            Field(description=field_description)
        )
    
    # Create the dynamic model
    return create_model(schema_name, **fields)


def _get_python_type(type_str: str) -> Type:
    """
    Convert string type to Python type.
    
    Args:
        type_str: String representation of the type
        
    Returns:
        Type: Corresponding Python type
    """
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
    
    return type_mapping.get(type_str.lower(), str)


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
        
        questions_list.append(f"- {output_name} ({data_type}): {question_text}")
    
    questions_str = "\n".join(questions_list)
    
    prompt = f"""Please analyze the following document and extract the requested information.

Document text:
{document_text}

Please answer the following questions based on the document content:
{questions_str}

Return your response as a JSON object with the exact field names specified above. If information is not available in the document, use null for the field value.

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
    try:
        return schema_class(**result)
    except Exception as e:
        raise ValueError(f"Failed to validate extraction result: {e}")


def schema_to_dict(schema_instance: BaseModel) -> Dict[str, Any]:
    """
    Convert schema instance to dictionary.
    
    Args:
        schema_instance: Validated Pydantic model instance
        
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
