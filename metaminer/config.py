"""
Configuration management for metaminer.
"""
import os
import logging
from typing import Optional
from pathlib import Path


class Config:
    """Configuration class for metaminer settings."""
    
    # API Configuration
    DEFAULT_BASE_URL = "http://localhost:5001/api/v1"
    DEFAULT_MODEL = "gpt-3.5-turbo"
    DEFAULT_TIMEOUT = 30.0
    DEFAULT_MAX_RETRIES = 3
    
    # Logging Configuration
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # File Processing Configuration
    MAX_FILE_SIZE_MB = 50
    SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.odt', '.rtf', '.txt', '.md', '.html', '.epub', '.tex']
    
    # Concurrency Configuration
    DEFAULT_MAX_CONCURRENT_REQUESTS = 3
    DEFAULT_REQUESTS_PER_MINUTE = 60
    DEFAULT_BATCH_SIZE = 100
    DEFAULT_ENABLE_PROGRESS_BAR = True
    
    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None,
                 max_concurrent_requests: Optional[int] = None, requests_per_minute: Optional[int] = None,
                 batch_size: Optional[int] = None, enable_progress_bar: Optional[bool] = None):
        # Priority: explicit args → environment → defaults
        self.api_key = api_key or self._get_api_key()
        self.base_url = base_url or self._get_base_url()
        self.model = model or self._get_model()
        self.timeout = self._get_timeout()
        self.max_retries = self._get_max_retries()
        self.log_level = self._get_log_level()
        
        # Concurrency settings
        self.max_concurrent_requests = max_concurrent_requests if max_concurrent_requests is not None else self._get_max_concurrent_requests()
        self.requests_per_minute = requests_per_minute if requests_per_minute is not None else self._get_requests_per_minute()
        self.batch_size = batch_size if batch_size is not None else self._get_batch_size()
        self.enable_progress_bar = enable_progress_bar if enable_progress_bar is not None else self._get_enable_progress_bar()
        
        # Make these instance attributes so they can be modified in tests
        self.MAX_FILE_SIZE_MB = self.MAX_FILE_SIZE_MB
        self.SUPPORTED_EXTENSIONS = self.SUPPORTED_EXTENSIONS
        
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment or return None."""
        return os.environ.get("OPENAI_API_KEY")
    
    def _get_base_url(self) -> str:
        """Get base URL from environment or use default."""
        return os.environ.get("METAMINER_BASE_URL", self.DEFAULT_BASE_URL)
    
    def _get_model(self) -> str:
        """Get model name from environment or use default."""
        return os.environ.get("METAMINER_MODEL", self.DEFAULT_MODEL)
    
    def _get_timeout(self) -> float:
        """Get timeout from environment or use default."""
        try:
            return float(os.environ.get("METAMINER_TIMEOUT", self.DEFAULT_TIMEOUT))
        except ValueError:
            return self.DEFAULT_TIMEOUT
    
    def _get_max_retries(self) -> int:
        """Get max retries from environment or use default."""
        try:
            return int(os.environ.get("METAMINER_MAX_RETRIES", self.DEFAULT_MAX_RETRIES))
        except ValueError:
            return self.DEFAULT_MAX_RETRIES
    
    def _get_log_level(self) -> str:
        """Get log level from environment or use default."""
        return os.environ.get("METAMINER_LOG_LEVEL", self.DEFAULT_LOG_LEVEL)
    
    def _get_max_concurrent_requests(self) -> int:
        """Get max concurrent requests from environment or use default."""
        try:
            return int(os.environ.get("METAMINER_MAX_CONCURRENT_REQUESTS", self.DEFAULT_MAX_CONCURRENT_REQUESTS))
        except ValueError:
            return self.DEFAULT_MAX_CONCURRENT_REQUESTS
    
    def _get_requests_per_minute(self) -> int:
        """Get requests per minute from environment or use default."""
        try:
            return int(os.environ.get("METAMINER_REQUESTS_PER_MINUTE", self.DEFAULT_REQUESTS_PER_MINUTE))
        except ValueError:
            return self.DEFAULT_REQUESTS_PER_MINUTE
    
    def _get_batch_size(self) -> int:
        """Get batch size from environment or use default."""
        try:
            return int(os.environ.get("METAMINER_BATCH_SIZE", self.DEFAULT_BATCH_SIZE))
        except ValueError:
            return self.DEFAULT_BATCH_SIZE
    
    def _get_enable_progress_bar(self) -> bool:
        """Get enable progress bar from environment or use default."""
        env_val = os.environ.get("METAMINER_ENABLE_PROGRESS_BAR", str(self.DEFAULT_ENABLE_PROGRESS_BAR))
        return env_val.lower() in ('true', '1', 'yes', 'on')
    
    def validate(self) -> None:
        """Validate configuration settings."""
        errors = []
        
        # Validate timeout
        if self.timeout <= 0:
            errors.append(f"Timeout must be positive, got: {self.timeout}")
        
        # Validate max_retries
        if self.max_retries < 0:
            errors.append(f"Max retries must be non-negative, got: {self.max_retries}")
        
        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_levels:
            errors.append(f"Invalid log level: {self.log_level}. Must be one of: {valid_levels}")
        
        # Validate concurrency settings
        if self.max_concurrent_requests <= 0:
            errors.append(f"Max concurrent requests must be positive, got: {self.max_concurrent_requests}")
        
        if self.requests_per_minute <= 0:
            errors.append(f"Requests per minute must be positive, got: {self.requests_per_minute}")
        
        if self.batch_size <= 0:
            errors.append(f"Batch size must be positive, got: {self.batch_size}")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))


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
    formatter = logging.Formatter(config.DEFAULT_LOG_FORMAT)
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
