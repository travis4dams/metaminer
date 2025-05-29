"""
Question parser module for reading questions from text and CSV files.
"""
import csv
import os
from typing import Dict, List, Any, Union
from pathlib import Path


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
                "output_name": field_name
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
                data_type = "str"  # default
                for header in headers:
                    if header.lower().strip() in ['data_type', 'type', 'dtype']:
                        type_value = row[header].strip().lower()
                        if type_value in ['str', 'string', 'text']:
                            data_type = "str"
                        elif type_value in ['int', 'integer', 'number']:
                            data_type = "int"
                        elif type_value in ['float', 'decimal']:
                            data_type = "float"
                        elif type_value in ['bool', 'boolean']:
                            data_type = "bool"
                        elif type_value in ['date', 'datetime']:
                            data_type = "date"
                        else:
                            data_type = "str"  # fallback
                        break
                
                questions[field_name] = {
                    "question": question_text,
                    "type": data_type,
                    "output_name": field_name
                }
    
    except Exception as e:
        raise ValueError(f"Failed to parse CSV file {file_path}: {e}")
    
    return questions


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
