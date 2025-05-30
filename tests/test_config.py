"""
Test suite for configuration management.
"""
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from metaminer.config import Config, setup_logging, validate_file_path, validate_questions


class TestConfig:
    """Test suite for Config class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.base_url == "http://localhost:5001/api/v1"
        assert config.model == "gpt-3.5-turbo"
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.log_level == "INFO"
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key',
        'METAMINER_BASE_URL': 'http://test.com/api',
        'METAMINER_MODEL': 'gpt-4',
        'METAMINER_TIMEOUT': '60.0',
        'METAMINER_MAX_RETRIES': '5',
        'METAMINER_LOG_LEVEL': 'DEBUG'
    })
    def test_environment_config(self):
        """Test configuration from environment variables."""
        config = Config()
        
        assert config.api_key == 'test-key'
        assert config.base_url == 'http://test.com/api'
        assert config.model == 'gpt-4'
        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.log_level == 'DEBUG'
    
    def test_config_validation_success(self):
        """Test successful configuration validation."""
        config = Config()
        # Should not raise any exception
        config.validate()
    
    def test_config_validation_invalid_timeout(self):
        """Test configuration validation with invalid timeout."""
        config = Config()
        config.timeout = -1
        
        with pytest.raises(ValueError, match="Timeout must be positive"):
            config.validate()
    
    def test_config_validation_invalid_retries(self):
        """Test configuration validation with invalid max_retries."""
        config = Config()
        config.max_retries = -1
        
        with pytest.raises(ValueError, match="Max retries must be non-negative"):
            config.validate()
    
    def test_config_validation_invalid_log_level(self):
        """Test configuration validation with invalid log level."""
        config = Config()
        config.log_level = "INVALID"
        
        with pytest.raises(ValueError, match="Invalid log level"):
            config.validate()
    
    @patch.dict(os.environ, {'METAMINER_TIMEOUT': 'invalid'})
    def test_invalid_environment_values(self):
        """Test handling of invalid environment variable values."""
        config = Config()
        # Should fall back to default values
        assert config.timeout == 30.0
    
    @patch.dict(os.environ, {'METAMINER_MAX_RETRIES': 'invalid'})
    def test_invalid_environment_retries(self):
        """Test handling of invalid max_retries environment value."""
        config = Config()
        # Should fall back to default values
        assert config.max_retries == 3


class TestLogging:
    """Test suite for logging setup."""
    
    def test_setup_logging(self):
        """Test logging setup."""
        config = Config()
        logger = setup_logging(config)
        
        assert logger.name == "metaminer"
        assert logger.level == getattr(__import__('logging'), config.log_level.upper())
    
    def test_setup_logging_no_duplicate_handlers(self):
        """Test that setup_logging doesn't add duplicate handlers."""
        config = Config()
        logger1 = setup_logging(config)
        logger2 = setup_logging(config)
        
        # Should be the same logger instance
        assert logger1 is logger2
        # Should not have duplicate handlers
        assert len(logger1.handlers) == 1


class TestFileValidation:
    """Test suite for file validation."""
    
    def test_validate_file_path_success(self):
        """Test successful file validation."""
        config = Config()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            # Should not raise any exception
            validate_file_path(tmp_path, config)
        finally:
            os.unlink(tmp_path)
    
    def test_validate_file_path_not_found(self):
        """Test file validation with non-existent file."""
        config = Config()
        
        with pytest.raises(FileNotFoundError, match="File not found"):
            validate_file_path("/nonexistent/file.txt", config)
    
    def test_validate_file_path_is_directory(self):
        """Test file validation with directory path."""
        config = Config()
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            with pytest.raises(ValueError, match="Path is not a file"):
                validate_file_path(tmp_dir, config)
    
    def test_validate_file_path_too_large(self):
        """Test file validation with oversized file."""
        config = Config()
        config.MAX_FILE_SIZE_MB = 0.001  # Very small limit for testing
        
        # Create a file larger than the limit
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b"x" * 2000)  # 2KB file
            tmp_path = tmp.name
        
        try:
            with pytest.raises(ValueError, match="File too large"):
                validate_file_path(tmp_path, config)
        finally:
            os.unlink(tmp_path)
    
    def test_validate_file_path_unsupported_format(self):
        """Test file validation with unsupported file format."""
        config = Config()
        
        # Create a file with unsupported extension
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                validate_file_path(tmp_path, config)
        finally:
            os.unlink(tmp_path)


class TestQuestionsValidation:
    """Test suite for questions validation."""
    
    def test_validate_questions_success(self):
        """Test successful questions validation."""
        questions = {
            "title": {
                "question": "What is the title?",
                "type": "str"
            },
            "author": {
                "question": "Who is the author?",
                "type": "str"
            }
        }
        
        # Should not raise any exception
        validate_questions(questions)
    
    def test_validate_questions_not_dict(self):
        """Test questions validation with non-dictionary input."""
        with pytest.raises(ValueError, match="Questions must be a dictionary"):
            validate_questions("not a dict")
    
    def test_validate_questions_empty(self):
        """Test questions validation with empty dictionary."""
        with pytest.raises(ValueError, match="Questions dictionary cannot be empty"):
            validate_questions({})
    
    def test_validate_questions_invalid_value_type(self):
        """Test questions validation with invalid value type."""
        questions = {
            "title": "not a dict"
        }
        
        with pytest.raises(ValueError, match="Question value for 'title' must be a dictionary"):
            validate_questions(questions)
    
    def test_validate_questions_missing_question_key(self):
        """Test questions validation with missing question key."""
        questions = {
            "title": {
                "type": "str"
                # Missing "question" key
            }
        }
        
        with pytest.raises(ValueError, match="Question dictionary for 'title' must contain 'question' key"):
            validate_questions(questions)
    
    def test_validate_questions_non_string_question(self):
        """Test questions validation with non-string question text."""
        questions = {
            "title": {
                "question": 123,  # Not a string
                "type": "str"
            }
        }
        
        with pytest.raises(ValueError, match="Question text for 'title' must be a string"):
            validate_questions(questions)
    
    def test_validate_questions_empty_question(self):
        """Test questions validation with empty question text."""
        questions = {
            "title": {
                "question": "   ",  # Empty/whitespace only
                "type": "str"
            }
        }
        
        with pytest.raises(ValueError, match="Question text for 'title' cannot be empty"):
            validate_questions(questions)
    
    def test_validate_questions_invalid_type(self):
        """Test questions validation with invalid type."""
        questions = {
            "title": {
                "question": "What is the title?",
                "type": "invalid_type"
            }
        }
        
        with pytest.raises(ValueError, match="Invalid type 'invalid_type' for question 'title'"):
            validate_questions(questions)
    
    def test_validate_questions_valid_types(self):
        """Test questions validation with all valid types."""
        valid_types = ["str", "string", "text", "int", "integer", "number", 
                      "float", "decimal", "bool", "boolean", "date", "datetime"]
        
        for valid_type in valid_types:
            questions = {
                "test": {
                    "question": "Test question?",
                    "type": valid_type
                }
            }
            # Should not raise any exception
            validate_questions(questions)
    
    def test_validate_questions_no_type_field(self):
        """Test questions validation without type field (should be valid)."""
        questions = {
            "title": {
                "question": "What is the title?"
                # No "type" field - should be valid
            }
        }
        
        # Should not raise any exception
        validate_questions(questions)


# Integration tests
class TestConfigIntegration:
    """Integration tests for configuration with other components."""
    
    @patch.dict(os.environ, {'METAMINER_LOG_LEVEL': 'DEBUG'})
    def test_config_with_logging(self):
        """Test configuration integration with logging."""
        config = Config()
        logger = setup_logging(config)
        
        assert logger.level == getattr(__import__('logging'), 'DEBUG')
    
    def test_config_with_file_validation(self):
        """Test configuration integration with file validation."""
        config = Config()
        
        # Create a valid test file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            # Should work with valid file
            validate_file_path(tmp_path, config)
            
            # Test with modified config - create a larger file for this test
            config.MAX_FILE_SIZE_MB = 0.001
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp2:
                tmp2.write(b"x" * 2000)  # 2KB file
                tmp2_path = tmp2.name
            
            try:
                with pytest.raises(ValueError, match="File too large"):
                    validate_file_path(tmp2_path, config)
            finally:
                os.unlink(tmp2_path)
        finally:
            os.unlink(tmp_path)
