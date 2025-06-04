"""
Question parser module for reading questions from text and CSV files.
"""
import csv
import os
from typing import Dict, List, Any, Union
from pathlib import Path
import re


def parse_questions_from_file(file_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse questions from a text or CSV file.
    
    Args:
        file_path: Path to the questions file (.txt or .csv)
        
    Returns:
        dict: Normalized questions dictionary
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is unsupported or invalid
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Questions file not found: {file_path}")
    
    file_path = Path(file_path)
    
    if file_path.suffix.lower() == '.txt':
        return _parse_text_file(file_path)
    elif file_path.suffix.lower() == '.csv':
        return _parse_csv_file(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}. Use .txt or .csv")


def _parse_text_file(file_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Parse questions from a text file (one question per line).
    
    Args:
        file_path: Path to the text file
        
    Returns:
        dict: Normalized questions dictionary
    """
    questions = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            lines = f.readlines()
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if line and not line.startswith('#'):  # Skip empty lines and comments
            field_name = f"question_{i}"
            questions[field_name] = {
                "question": line,
                "type": "str",
                "output_name": field_name,
                "_type_explicit": False  # Text files don't specify types explicitly
            }
    
    return questions


def _parse_csv_file(file_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Parse questions from a CSV file.
    
    Expected CSV formats:
    1. Single column 'question': One question per row
    2. Multiple columns: 'question', 'field_name', 'data_type'
    3. Multiple columns: 'question', 'field_name' (type defaults to str)
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        dict: Normalized questions dictionary
    """
    questions = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Detect delimiter
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(f, delimiter=delimiter)
            headers = reader.fieldnames
            
            if not headers:
                raise ValueError("CSV file appears to be empty or invalid")
            
            # Normalize header names (case-insensitive)
            headers_lower = [h.lower().strip() for h in headers]
            
            for i, row in enumerate(reader, 1):
                if not any(row.values()):  # Skip empty rows
                    continue
                
                # Extract question text
                question_text = None
                for header in headers:
                    if header.lower().strip() in ['question', 'q', 'text']:
                        question_text = row[header].strip()
                        break
                
                if not question_text:
                    # If no 'question' column, use the first column
                    question_text = list(row.values())[0].strip()
                
                if not question_text:
                    continue
                
                # Extract field name
                field_name = None
                for header in headers:
                    if header.lower().strip() in ['field_name', 'field', 'name', 'output_name']:
                        field_name = row[header].strip()
                        break
                
                if not field_name:
                    field_name = f"question_{i}"
                
                # Extract data type
                data_type = None  # No default - will be set based on whether type is explicit
                type_explicit = False
                for header in headers:
                    if header.lower().strip() in ['data_type', 'type', 'dtype']:
                        type_value = row[header].strip()  # Don't convert to lowercase yet
                        if type_value:  # Only if there's actually a value
                            type_explicit = True
                            type_value_lower = type_value.lower()
                            if type_value_lower in ['str', 'string', 'text']:
                                data_type = "str"
                            elif type_value_lower in ['int', 'integer', 'number']:
                                data_type = "int"
                            elif type_value_lower in ['float', 'decimal']:
                                data_type = "float"
                            elif type_value_lower in ['bool', 'boolean']:
                                data_type = "bool"
                            elif type_value_lower in ['date', 'datetime']:
                                data_type = "date"
                            elif _is_valid_array_type(type_value_lower):
                                data_type = type_value  # Keep original case for array type
                            elif _is_valid_enum_type(type_value_lower):
                                data_type = type_value  # Keep original case for enum type
                            else:
                                data_type = "str"  # fallback
                        break
                
                # Extract default value
                default_value = None
                for header in headers:
                    if header.lower().strip() in ['default_value', 'default', 'default_val']:
                        default_raw = row[header]
                        if default_raw is not None:  # Check for None first
                            default_raw = default_raw.strip()
                            if default_raw:  # Only if there's actually a value
                                default_value = default_raw
                        break
                
                # Set default only if no explicit type was provided
                if data_type is None:
                    data_type = "str"
                    type_explicit = False
                
                question_dict = {
                    "question": question_text,
                    "type": data_type,
                    "output_name": field_name,
                    "_type_explicit": type_explicit
                }
                
                # Add default value if specified and validate it
                if default_value is not None:
                    try:
                        validated_default = _validate_default_value(default_value, data_type, field_name)
                        question_dict["default"] = validated_default
                    except ValueError as e:
                        raise ValueError(f"Invalid default value in CSV row {i}: {e}")
                
                questions[field_name] = question_dict
    
    except Exception as e:
        raise ValueError(f"Failed to parse CSV file {file_path}: {e}")
    
    return questions


def _is_valid_array_type(type_str: str) -> bool:
    """
    Check if a type string represents a valid array type specification.
    
    Args:
        type_str: String representation of the type
        
    Returns:
        bool: True if it's a valid array type specification
    """
    type_str = type_str.strip().lower()
    
    # Check if this matches the list(type) pattern
    if not (type_str.startswith("list(") and type_str.endswith(")")):
        return False
    
    # Extract the base type
    base_type = type_str[5:-1].strip()
    
    # Valid base types for arrays
    valid_base_types = {
        'str', 'string', 'text',
        'int', 'integer', 'number',
        'float', 'decimal',
        'bool', 'boolean',
        'date', 'datetime'
    }
    
    return base_type in valid_base_types


def _is_valid_enum_type(type_str: str) -> bool:
    """
    Check if a type string represents a valid enum type specification.
    
    Args:
        type_str: String representation of the type
        
    Returns:
        bool: True if it's a valid enum type specification
    """
    type_str = type_str.strip().lower()
    
    # Check if this matches enum(val1,val2,...) or multi_enum(val1,val2,...) pattern
    if type_str.startswith("enum(") and type_str.endswith(")"):
        return _validate_enum_values(type_str[5:-1])
    elif type_str.startswith("multi_enum(") and type_str.endswith(")"):
        return _validate_enum_values(type_str[11:-1])
    
    return False


def _validate_enum_values(values_str: str) -> bool:
    """
    Validate that enum values string contains valid comma-separated values.
    
    Args:
        values_str: Comma-separated values string
        
    Returns:
        bool: True if valid
    """
    if not values_str.strip():
        return False
    
    # Split by comma and check each value
    values = [v.strip() for v in values_str.split(',')]
    
    # Must have at least one value, and all values must be non-empty
    return len(values) > 0 and all(v for v in values)


def _extract_enum_values(type_str: str) -> List[str]:
    """
    Extract enum values from type string.
    
    Args:
        type_str: Type string like 'enum(val1,val2,val3)' or 'multi_enum(val1,val2,val3)'
        
    Returns:
        List[str]: List of enum values
    """
    type_str = type_str.strip()
    
    if type_str.startswith("enum(") and type_str.endswith(")"):
        values_str = type_str[5:-1]
    elif type_str.startswith("multi_enum(") and type_str.endswith(")"):
        values_str = type_str[11:-1]
    else:
        return []
    
    # Split by comma and clean up values
    values = [v.strip() for v in values_str.split(',')]
    return [v for v in values if v]  # Filter out empty values


def _validate_default_value(default_value: str, data_type: str, field_name: str) -> Any:
    """
    Validate and convert default value based on data type.
    
    Args:
        default_value: Raw default value string from CSV
        data_type: Data type specification
        field_name: Field name for error messages
        
    Returns:
        Any: Converted default value
        
    Raises:
        ValueError: If default value is invalid for the data type
    """
    if default_value is None:
        return None
    
    # Handle enum types first
    is_enum, is_multi, enum_values = _parse_enum_type(data_type)
    if is_enum:
        if is_multi:
            # Multi-enum: parse comma-separated values
            default_list = [v.strip() for v in default_value.split(',')]
            for val in default_list:
                if val not in enum_values:
                    raise ValueError(f"Default value '{val}' for field '{field_name}' is not in enum values: {enum_values}")
            return default_list
        else:
            # Single enum: validate single value
            if default_value not in enum_values:
                raise ValueError(f"Default value '{default_value}' for field '{field_name}' is not in enum values: {enum_values}")
            return default_value
    
    # Handle array types
    is_array, base_type_str = _parse_array_type(data_type)
    if is_array:
        raise ValueError(f"Default values are not supported for array types (field '{field_name}')")
    
    # Handle basic types
    type_lower = data_type.lower()
    
    if type_lower in ['str', 'string', 'text']:
        return default_value
    
    elif type_lower in ['int', 'integer', 'number']:
        try:
            return int(default_value)
        except ValueError:
            raise ValueError(f"Default value '{default_value}' for field '{field_name}' cannot be converted to integer")
    
    elif type_lower in ['float', 'decimal']:
        try:
            return float(default_value)
        except ValueError:
            raise ValueError(f"Default value '{default_value}' for field '{field_name}' cannot be converted to float")
    
    elif type_lower in ['bool', 'boolean']:
        lower_val = default_value.lower()
        if lower_val in ['true', '1', 'yes', 'on']:
            return True
        elif lower_val in ['false', '0', 'no', 'off']:
            return False
        else:
            raise ValueError(f"Default value '{default_value}' for field '{field_name}' is not a valid boolean (use true/false, 1/0, yes/no, on/off)")
    
    elif type_lower in ['date', 'datetime']:
        # For date/datetime, we'll validate the format but keep as string
        # The actual parsing will happen in the schema builder
        try:
            from dateutil import parser as date_parser
            date_parser.parse(default_value)  # Just validate it can be parsed
            return default_value
        except (ValueError, TypeError):
            raise ValueError(f"Default value '{default_value}' for field '{field_name}' is not a valid date/datetime format")
    
    else:
        # Unknown type, treat as string
        return default_value


def _parse_enum_type(type_str: str) -> tuple:
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


def _parse_array_type(type_str: str) -> tuple:
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

 
def validate_questions(questions: Dict[str, Dict[str, Any]]) -> bool:
    """
    Validate the structure of parsed questions.
    
    Args:
        questions: Questions dictionary to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        ValueError: If validation fails
    """
    if not questions:
        raise ValueError("No questions found")
    
    for field_name, question_data in questions.items():
        if not isinstance(question_data, dict):
            raise ValueError(f"Invalid question data for {field_name}")
        
        if "question" not in question_data:
            raise ValueError(f"Missing 'question' field for {field_name}")
        
        if not question_data["question"].strip():
            raise ValueError(f"Empty question text for {field_name}")
        
        if "type" not in question_data:
            question_data["type"] = "str"  # Set default
        
        if "output_name" not in question_data:
            question_data["output_name"] = field_name  # Set default
    
    return True
