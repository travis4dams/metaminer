"""
Configuration management for metaminer using pydantic-settings.
"""
import logging
from typing import Optional, List
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Configuration class for metaminer settings using pydantic-settings."""
    
    # API Configuration
    api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    base_url: str = Field(default="http://localhost:5001/api/v1", alias="METAMINER_BASE_URL")
    model: str = Field(default="gpt-3.5-turbo", alias="METAMINER_MODEL")
    timeout: float = Field(default=30.0, alias="METAMINER_TIMEOUT", gt=0)
    max_retries: int = Field(default=3, alias="METAMINER_MAX_RETRIES", ge=0)
    
    # Logging Configuration
    log_level: str = Field(default="INFO", alias="METAMINER_LOG_LEVEL")
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # File Processing Configuration
    max_file_size_mb: int = Field(default=50, gt=0)
    supported_extensions: List[str] = Field(default_factory=lambda: [
        '.pdf', '.docx', '.doc', '.odt', '.rtf', '.txt', '.md', '.html', '.epub', '.tex'
    ])
    
    # Concurrency Configuration
    max_concurrent_requests: int = Field(default=3, alias="METAMINER_MAX_CONCURRENT_REQUESTS", gt=0)
    requests_per_minute: int = Field(default=60, alias="METAMINER_REQUESTS_PER_MINUTE", gt=0)
    batch_size: int = Field(default=100, alias="METAMINER_BATCH_SIZE", gt=0)
    enable_progress_bar: bool = Field(default=True, alias="METAMINER_ENABLE_PROGRESS_BAR")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of: {valid_levels}")
        return v.upper()
    
    @field_validator('supported_extensions')
    @classmethod
    def validate_extensions(cls, v: List[str]) -> List[str]:
        """Validate supported extensions format."""
        for ext in v:
            if not ext.startswith('.'):
                raise ValueError(f"Extension must start with '.': {ext}")
        return v
    
    # Legacy properties for backwards compatibility
    @property
    def MAX_FILE_SIZE_MB(self) -> int:
        """Legacy property for backwards compatibility."""
        return self.max_file_size_mb
    
    @MAX_FILE_SIZE_MB.setter
    def MAX_FILE_SIZE_MB(self, value: int):
        """Legacy setter for backwards compatibility."""
        self.max_file_size_mb = value
    
    @property
    def SUPPORTED_EXTENSIONS(self) -> List[str]:
        """Legacy property for backwards compatibility."""
        return self.supported_extensions
    
    @SUPPORTED_EXTENSIONS.setter
    def SUPPORTED_EXTENSIONS(self, value: List[str]):
        """Legacy setter for backwards compatibility."""
        self.supported_extensions = value
    

def setup_logging(config: Config) -> logging.Logger:
    """
    Set up logging for metaminer.
    
    Args:
        config: Configuration instance
        
    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger("metaminer")
    
    # Set log level (always update it)
    log_level = getattr(logging, config.log_level.upper())
    logger.setLevel(log_level)
    
    # Don't add handlers if they already exist
    if logger.handlers:
        # Update existing handler levels
        for handler in logger.handlers:
            handler.setLevel(log_level)
        return logger
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(config.log_format)
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


def validate_file_path(file_path: str, config: Config) -> None:
    """
    Validate file path and size.
    
    Args:
        file_path: Path to the file
        config: Configuration instance
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is too large or unsupported format
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    # Check file size
    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > config.MAX_FILE_SIZE_MB:
        raise ValueError(
            f"File too large: {file_size_mb:.1f}MB. "
            f"Maximum allowed: {config.MAX_FILE_SIZE_MB}MB"
        )
    
    # Check file extension
    if path.suffix.lower() not in config.SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {path.suffix}. "
            f"Supported formats: {config.SUPPORTED_EXTENSIONS}"
        )


def validate_questions(questions: dict) -> None:
    """
    Validate questions dictionary format.
    
    Args:
        questions: Questions dictionary
        
    Raises:
        ValueError: If questions format is invalid
    """
    if not isinstance(questions, dict):
        raise ValueError("Questions must be a dictionary")
    
    if not questions:
        raise ValueError("Questions dictionary cannot be empty")
    
    for key, value in questions.items():
        if not isinstance(value, dict):
            raise ValueError(f"Question value for '{key}' must be a dictionary")
        
        if "question" not in value:
            raise ValueError(f"Question dictionary for '{key}' must contain 'question' key")
        
        if not isinstance(value["question"], str):
            raise ValueError(f"Question text for '{key}' must be a string")
        
        if not value["question"].strip():
            raise ValueError(f"Question text for '{key}' cannot be empty")
        
        # Validate type if present
        if "type" in value:
            valid_types = ["str", "string", "text", "int", "integer", "number", 
                          "float", "decimal", "bool", "boolean", "date", "datetime"]
            
            # Check if it's a valid array type
            if _is_valid_array_type(value["type"]):
                # Array type is valid
                pass
            # Check if it's a valid enum type
            elif _is_valid_enum_type(value["type"]):
                # Enum type is valid
                pass
            elif value["type"].lower() not in valid_types:
                raise ValueError(
                    f"Invalid type '{value['type']}' for question '{key}'. "
                    f"Valid types: {valid_types} or array types like list(str), list(int), etc., or enum types like enum(val1,val2,val3)"
                )


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
