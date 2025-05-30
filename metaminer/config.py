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
    
    def __init__(self):
        self.api_key = self._get_api_key()
        self.base_url = self._get_base_url()
        self.model = self._get_model()
        self.timeout = self._get_timeout()
        self.max_retries = self._get_max_retries()
        self.log_level = self._get_log_level()
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
            if value["type"].lower() not in valid_types:
                raise ValueError(
                    f"Invalid type '{value['type']}' for question '{key}'. "
                    f"Valid types: {valid_types}"
                )
