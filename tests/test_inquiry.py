import pytest
from unittest.mock import MagicMock, patch
from metaminer.inquiry import Inquiry

@pytest.fixture
def mock_openai():
    with patch('openai.OpenAI') as mock_client:
        yield mock_client

@pytest.fixture
def inquiry(mock_openai):
    return Inquiry(client=mock_openai, questions='Who is the document author?')


@pytest.fixture
def inquiry_list(mock_openai):
    return Inquiry(client=mock_openai, questions=['Who is the document author?', 'When was the document written?'])


@pytest.fixture
def inquiry_struct_list(mock_openai):
    return Inquiry(client=mock_openai, questions=[{'question': 'Who is the document author?'}])


class TestInquirySingleString:
    """Test suite for Inquiry objects with single string questions"""
    
    def test_process_documents_single(self, inquiry, mock_openai):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_openai.chat.completions.create.return_value = mock_response

        result = inquiry.process_documents("Sample document")
        assert result == ["Test response"]

    def test_process_documents_list(self, inquiry, mock_openai):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_openai.chat.completions.create.return_value = mock_response

        result = inquiry.process_documents(["Doc 1", "Doc 2"])
        assert result == ["Test response", "Test response"]


class TestInquiryListString:
    """Test suite for Inquiry objects with list of string questions"""
    
    def test_process_documents_single(self, inquiry_list, mock_openai):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_openai.chat.completions.create.return_value = mock_response

        result = inquiry_list.process_documents("Sample document")
        assert result == ["Test response"]

    def test_process_documents_list(self, inquiry_list, mock_openai):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_openai.chat.completions.create.return_value = mock_response

        result = inquiry_list.process_documents(["Doc 1", "Doc 2"])
        assert result == ["Test response", "Test response"]


class TestInquiryStructList:
    """Test suite for Inquiry objects with structured list questions"""
    
    def test_process_documents_single(self, inquiry_struct_list, mock_openai):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_openai.chat.completions.create.return_value = mock_response

        result = inquiry_struct_list.process_documents("Sample document")
        assert result == ["Test response"]

    def test_process_documents_list(self, inquiry_struct_list, mock_openai):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_openai.chat.completions.create.return_value = mock_response

        result = inquiry_struct_list.process_documents(["Doc 1", "Doc 2"])
        assert result == ["Test response", "Test response"]
