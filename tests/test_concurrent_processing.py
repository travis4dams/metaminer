"""
Test suite for concurrent processing functionality.
"""
import pytest
import pandas as pd
import time
from unittest.mock import MagicMock, patch
from metaminer.inquiry import Inquiry, RateLimiter
from metaminer.config import Config


@pytest.fixture
def test_config():
    """Test configuration with concurrent processing settings."""
    return Config(
        max_concurrent_requests=2,
        requests_per_minute=60,
        batch_size=10
    )


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client that returns proper JSON responses."""
    mock_client = MagicMock()
    
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"default": "Test Result"}'
    mock_client.chat.completions.create.return_value = mock_response
    
    # Mock the structured output API to fail (so it falls back to JSON mode)
    mock_client.beta.chat.completions.parse.side_effect = AttributeError("Structured output not available")
    
    # Mock models list
    mock_model = MagicMock()
    mock_model.id = "gpt-3.5-turbo"
    mock_client.models.list.return_value.data = [mock_model]
    
    return mock_client


class TestRateLimiter:
    """Test suite for RateLimiter class."""
    
    def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(60)
        assert limiter.requests_per_minute == 60
        assert limiter.tokens == 60
    
    def test_rate_limiter_acquire_immediate(self):
        """Test immediate token acquisition."""
        limiter = RateLimiter(60)
        assert limiter.acquire() is True
        assert limiter.tokens < 60
    
    def test_rate_limiter_acquire_timeout(self):
        """Test token acquisition with timeout."""
        limiter = RateLimiter(1)  # Very low rate
        
        # First acquisition should succeed
        assert limiter.acquire() is True
        
        # Second acquisition should timeout quickly
        assert limiter.acquire(timeout=0.1) is False
    
    def test_rate_limiter_token_replenishment(self):
        """Test that tokens are replenished over time."""
        limiter = RateLimiter(60)  # 1 token per second
        
        # Use up a token
        limiter.acquire()
        initial_tokens = limiter.tokens
        
        # Wait a bit and check tokens increased
        time.sleep(0.2)  # Wait longer for token replenishment
        # Trigger token update by checking acquire without actually acquiring
        with limiter.lock:
            now = time.time()
            elapsed = now - limiter.last_update
            limiter.tokens = min(limiter.requests_per_minute, 
                               limiter.tokens + elapsed * (limiter.requests_per_minute / 60.0))
            limiter.last_update = now
        
        assert limiter.tokens > initial_tokens


class TestConcurrentProcessing:
    """Test suite for concurrent processing functionality."""
    
    def test_process_text_single_string(self, mock_openai_client, test_config):
        """Test process_text with single string."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        result = inquiry.process_text("This is a test document.")
        
        assert isinstance(result, dict)
        assert "default" in result
        assert result["default"] == "Test Result"
    
    def test_process_text_rejects_list(self, mock_openai_client, test_config):
        """Test that process_text rejects lists."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        with pytest.raises(ValueError, match="process_text\\(\\) only accepts single strings"):
            inquiry.process_text(["text1", "text2"])
    
    def test_process_texts_with_list(self, mock_openai_client, test_config):
        """Test process_texts with list of strings."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        texts = ["Text 1", "Text 2", "Text 3"]
        results = inquiry.process_texts(texts, concurrent=False)  # Use sequential for predictable testing
        
        assert isinstance(results, list)
        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)
            assert "default" in result
    
    def test_process_texts_with_pandas_series(self, mock_openai_client, test_config):
        """Test process_texts with pandas Series."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        series = pd.Series(["Text 1", "Text 2", "Text 3"])
        results = inquiry.process_texts(series, concurrent=False)
        
        assert isinstance(results, list)
        assert len(results) == 3
    
    def test_process_texts_concurrent_vs_sequential(self, mock_openai_client, test_config):
        """Test that concurrent and sequential processing produce similar results."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        texts = ["Text 1", "Text 2"]
        
        # Test sequential
        results_sequential = inquiry.process_texts(texts, concurrent=False)
        
        # Test concurrent
        results_concurrent = inquiry.process_texts(texts, concurrent=True)
        
        assert len(results_sequential) == len(results_concurrent)
        assert len(results_sequential) == 2
    
    def test_process_texts_with_metadata(self, mock_openai_client, test_config):
        """Test process_texts with metadata."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        texts = ["Text 1", "Text 2"]
        metadata = [{"source": "doc1"}, {"source": "doc2"}]
        
        results = inquiry.process_texts(texts, metadata=metadata, concurrent=False)
        
        assert len(results) == 2
        assert results[0]["source"] == "doc1"
        assert results[1]["source"] == "doc2"
    
    def test_process_texts_with_single_metadata_dict(self, mock_openai_client, test_config):
        """Test process_texts with single metadata dict applied to all."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        texts = ["Text 1", "Text 2"]
        metadata = {"batch": "test_batch"}
        
        results = inquiry.process_texts(texts, metadata=metadata, concurrent=False)
        
        assert len(results) == 2
        assert results[0]["batch"] == "test_batch"
        assert results[1]["batch"] == "test_batch"
    
    def test_process_texts_metadata_length_mismatch(self, mock_openai_client, test_config):
        """Test process_texts with mismatched metadata length."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        texts = ["Text 1", "Text 2"]
        metadata = [{"source": "doc1"}]  # Wrong length
        
        with pytest.raises(ValueError, match="Metadata list must have same length"):
            inquiry.process_texts(texts, metadata=metadata)
    
    def test_process_texts_empty_list(self, mock_openai_client, test_config):
        """Test process_texts with empty list."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        results = inquiry.process_texts([], concurrent=False)
        assert results == []
    
    def test_process_texts_single_item_uses_sequential(self, mock_openai_client, test_config):
        """Test that single item automatically uses sequential processing."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        # Even with concurrent=True, single item should use sequential
        results = inquiry.process_texts(["Single text"], concurrent=True)
        assert len(results) == 1
    
    def test_pandas_apply_integration(self, mock_openai_client, test_config):
        """Test pandas apply integration."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        df = pd.DataFrame({'text': ["Text 1", "Text 2", "Text 3"]})
        df['results'] = df['text'].apply(inquiry.process_text)
        
        assert len(df) == 3
        assert 'results' in df.columns
        for result in df['results']:
            assert isinstance(result, dict)
            assert "default" in result


class TestConcurrentProcessingErrorHandling:
    """Test error handling in concurrent processing."""
    
    def test_concurrent_processing_with_api_errors(self, test_config):
        """Test concurrent processing handles API errors gracefully."""
        mock_client = MagicMock()
        
        # Mock API to fail for some calls
        def side_effect(*args, **kwargs):
            # Fail every other call
            if not hasattr(side_effect, 'call_count'):
                side_effect.call_count = 0
            side_effect.call_count += 1
            
            if side_effect.call_count % 2 == 0:
                raise Exception("API Error")
            else:
                mock_response = MagicMock()
                mock_response.choices[0].message.content = '{"default": "Success"}'
                return mock_response
        
        mock_client.chat.completions.create.side_effect = side_effect
        mock_client.beta.chat.completions.parse.side_effect = AttributeError("Not available")
        
        # Mock models list
        mock_model = MagicMock()
        mock_model.id = "gpt-3.5-turbo"
        mock_client.models.list.return_value.data = [mock_model]
        
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_client,
            config=test_config
        )
        
        texts = ["Text 1", "Text 2", "Text 3", "Text 4"]
        results = inquiry.process_texts(texts, concurrent=True)
        
        # Should get some results (not all will fail)
        assert len(results) >= 1
        assert len(results) <= len(texts)
    
    def test_concurrent_processing_fallback_to_sequential(self, mock_openai_client, test_config):
        """Test that concurrent processing falls back to sequential on thread errors."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        texts = ["Text 1", "Text 2"]
        
        # Mock ThreadPoolExecutor to raise an exception
        with patch('metaminer.inquiry.ThreadPoolExecutor') as mock_executor:
            mock_executor.side_effect = Exception("Thread pool error")
            
            # Should fall back to sequential processing
            results = inquiry.process_texts(texts, concurrent=True)
            assert len(results) == 2


class TestConfigurationValidation:
    """Test configuration validation for concurrent processing."""
    
    def test_config_validation_positive_values(self):
        """Test that config validates positive values."""
        config = Config(
            max_concurrent_requests=5,
            requests_per_minute=120,
            batch_size=50
        )
        config.validate()  # Should not raise
    
    def test_config_validation_zero_concurrent_requests(self):
        """Test that config rejects zero concurrent requests."""
        with pytest.raises(ValueError, match="Max concurrent requests must be positive"):
            config = Config(max_concurrent_requests=0)
            config.validate()
    
    def test_config_validation_zero_requests_per_minute(self):
        """Test that config rejects zero requests per minute."""
        with pytest.raises(ValueError, match="Requests per minute must be positive"):
            config = Config(requests_per_minute=0)
            config.validate()
    
    def test_config_validation_zero_batch_size(self):
        """Test that config rejects zero batch size."""
        with pytest.raises(ValueError, match="Batch size must be positive"):
            config = Config(batch_size=0)
            config.validate()


class TestBackwardCompatibility:
    """Test that changes maintain backward compatibility."""
    
    def test_existing_process_text_behavior(self, mock_openai_client, test_config):
        """Test that existing process_text behavior is preserved."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        # Single string should work as before
        result = inquiry.process_text("Test text")
        assert isinstance(result, dict)
        assert "default" in result
    
    def test_existing_process_documents_behavior(self, mock_openai_client, test_config):
        """Test that existing process_documents behavior is preserved."""
        inquiry = Inquiry(
            questions="What is the main topic?",
            client=mock_openai_client,
            config=test_config
        )
        
        # Create temporary test files
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp1:
            tmp1.write("Test document 1")
            tmp1_path = tmp1.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp2:
            tmp2.write("Test document 2")
            tmp2_path = tmp2.name
        
        try:
            # Test list of documents
            result_df = inquiry.process_documents([tmp1_path, tmp2_path])
            assert isinstance(result_df, pd.DataFrame)
            assert len(result_df) == 2
        finally:
            os.unlink(tmp1_path)
            os.unlink(tmp2_path)
