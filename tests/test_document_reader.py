"""
Test suite for document reader functionality.
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from metaminer.document_reader import (
    extract_text_from_pdf,
    extract_text,
    extract_text_from_directory,
    get_supported_extensions
)


class TestExtractTextFromPDF:
    """Test suite for PDF text extraction."""
    
    @patch('metaminer.document_reader.pymupdf')
    def test_extract_text_from_pdf_success(self, mock_pymupdf):
        """Test successful PDF text extraction."""
        # Mock PyMuPDF
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Sample PDF text content"
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_pymupdf.open.return_value = mock_doc
        
        result = extract_text_from_pdf("test.pdf")
        
        assert result == "Sample PDF text content"
        mock_pymupdf.open.assert_called_once_with("test.pdf")
        mock_doc.close.assert_called_once()
    
    @patch('metaminer.document_reader.pymupdf', None)
    def test_extract_text_from_pdf_no_pymupdf(self):
        """Test PDF extraction when PyMuPDF is not installed."""
        with pytest.raises(RuntimeError, match="PyMuPDF is not installed"):
            extract_text_from_pdf("test.pdf")
    
    @patch('metaminer.document_reader.pymupdf')
    def test_extract_text_from_pdf_error(self, mock_pymupdf):
        """Test PDF extraction error handling."""
        mock_pymupdf.open.side_effect = Exception("PDF read error")
        
        with pytest.raises(RuntimeError, match="Failed to extract text from PDF"):
            extract_text_from_pdf("test.pdf")


class TestExtractText:
    """Test suite for general text extraction."""
    
    def test_extract_text_nonexistent_file(self):
        """Test text extraction from non-existent file."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            extract_text("/nonexistent/file.txt")
    
    @patch('metaminer.document_reader.extract_text_from_pdf')
    def test_extract_text_pdf_file(self, mock_pdf_extract):
        """Test text extraction from PDF file."""
        mock_pdf_extract.return_value = "PDF content"
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            result = extract_text(tmp_path)
            assert result == "PDF content"
            mock_pdf_extract.assert_called_once_with(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    @patch('metaminer.document_reader.pypandoc')
    def test_extract_text_pandoc_success(self, mock_pypandoc):
        """Test text extraction using pandoc."""
        mock_pypandoc.convert_file.return_value = "Pandoc extracted text"
        
        # Create temporary DOCX file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            tmp.write(b"dummy content")
            tmp_path = tmp.name
        
        try:
            result = extract_text(tmp_path)
            assert result == "Pandoc extracted text"
            mock_pypandoc.convert_file.assert_called_once_with(tmp_path, 'plain')
        finally:
            os.unlink(tmp_path)
    
    @patch('metaminer.document_reader.pypandoc')
    def test_extract_text_pandoc_not_installed(self, mock_pypandoc):
        """Test text extraction when pandoc is not installed."""
        mock_pypandoc.convert_file.side_effect = OSError("pandoc not found")
        
        # Create temporary DOCX file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            tmp.write(b"dummy content")
            tmp_path = tmp.name
        
        try:
            with pytest.raises(RuntimeError, match="Pandoc is not installed"):
                extract_text(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def test_extract_text_txt_file_utf8(self):
        """Test text extraction from UTF-8 text file."""
        content = "This is a test document with UTF-8 content: café"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            result = extract_text(tmp_path)
            assert result == content
        finally:
            os.unlink(tmp_path)
    
    def test_extract_text_txt_file_latin1_fallback(self):
        """Test text extraction from text file with latin-1 encoding fallback."""
        content = "This is a test document"
        
        # Create file with latin-1 encoding
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='latin-1', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Mock UnicodeDecodeError for UTF-8, should fallback to latin-1
            with patch('builtins.open', side_effect=[
                UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte'),
                open(tmp_path, 'r', encoding='latin-1')
            ]):
                result = extract_text(tmp_path)
                assert content in result
        finally:
            os.unlink(tmp_path)
    
    @patch('metaminer.document_reader.pypandoc')
    def test_extract_text_unsupported_format_error(self, mock_pypandoc):
        """Test text extraction error for unsupported format."""
        mock_pypandoc.convert_file.side_effect = Exception("Unsupported format")
        
        # Create temporary file with unsupported extension
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as tmp:
            tmp.write(b"dummy content")
            tmp_path = tmp.name
        
        try:
            with pytest.raises(RuntimeError, match="Failed to extract text"):
                extract_text(tmp_path)
        finally:
            os.unlink(tmp_path)


class TestExtractTextFromDirectory:
    """Test suite for directory text extraction."""
    
    def test_extract_text_from_directory_success(self):
        """Test successful directory text extraction."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create test files
            txt_file = Path(tmp_dir) / "test1.txt"
            txt_file.write_text("Content of test1.txt")
            
            md_file = Path(tmp_dir) / "test2.md"
            md_file.write_text("# Markdown content")
            
            # Create unsupported file (should be ignored)
            unsupported_file = Path(tmp_dir) / "test.xyz"
            unsupported_file.write_text("Unsupported content")
            
            result = extract_text_from_directory(tmp_dir)
            
            assert len(result) == 2  # Only supported files
            assert str(txt_file) in result
            assert str(md_file) in result
            assert result[str(txt_file)] == "Content of test1.txt"
            assert "Markdown content" in result[str(md_file)]
    
    def test_extract_text_from_directory_nonexistent(self):
        """Test directory extraction from non-existent directory."""
        with pytest.raises(FileNotFoundError, match="Directory not found"):
            extract_text_from_directory("/nonexistent/directory")
    
    def test_extract_text_from_directory_not_directory(self):
        """Test directory extraction when path is not a directory."""
        with tempfile.NamedTemporaryFile() as tmp:
            with pytest.raises(ValueError, match="Path is not a directory"):
                extract_text_from_directory(tmp.name)
    
    def test_extract_text_from_directory_custom_extensions(self):
        """Test directory extraction with custom extensions."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create test files
            txt_file = Path(tmp_dir) / "test1.txt"
            txt_file.write_text("Content of test1.txt")
            
            pdf_file = Path(tmp_dir) / "test2.pdf"
            pdf_file.write_bytes(b"dummy pdf content")
            
            md_file = Path(tmp_dir) / "test3.md"
            md_file.write_text("# Markdown content")
            
            # Only extract .txt files
            result = extract_text_from_directory(tmp_dir, extensions=['.txt'])
            
            assert len(result) == 1
            assert str(txt_file) in result
            assert str(pdf_file) not in result
            assert str(md_file) not in result
    
    def test_extract_text_from_directory_with_errors(self):
        """Test directory extraction with some files causing errors."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create valid file
            txt_file = Path(tmp_dir) / "test1.txt"
            txt_file.write_text("Valid content")
            
            # Create file that will cause error (empty PDF)
            pdf_file = Path(tmp_dir) / "test2.pdf"
            pdf_file.write_bytes(b"")  # Empty file will cause extraction error
            
            # Should continue processing despite errors
            result = extract_text_from_directory(tmp_dir)
            
            # Should have at least the valid file
            assert str(txt_file) in result
            assert result[str(txt_file)] == "Valid content"


class TestGetSupportedExtensions:
    """Test suite for supported extensions function."""
    
    def test_get_supported_extensions(self):
        """Test getting list of supported extensions."""
        extensions = get_supported_extensions()
        
        assert isinstance(extensions, list)
        assert len(extensions) > 0
        
        # Check for common extensions
        assert '.pdf' in extensions
        assert '.txt' in extensions
        assert '.docx' in extensions
        assert '.md' in extensions
        assert '.html' in extensions
        
        # All extensions should start with dot
        for ext in extensions:
            assert ext.startswith('.')


class TestDocumentReaderIntegration:
    """Integration tests for document reader functionality."""
    
    def test_full_workflow_with_multiple_formats(self):
        """Test complete workflow with multiple document formats."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create test files of different formats
            txt_file = Path(tmp_dir) / "document1.txt"
            txt_file.write_text("This is a plain text document.")
            
            md_file = Path(tmp_dir) / "document2.md"
            md_file.write_text("# Markdown Document\n\nThis is markdown content.")
            
            html_file = Path(tmp_dir) / "document3.html"
            html_file.write_text("<html><body><h1>HTML Document</h1><p>HTML content</p></body></html>")
            
            # Test individual file extraction
            txt_content = extract_text(str(txt_file))
            assert "plain text document" in txt_content
            
            md_content = extract_text(str(md_file))
            assert "Markdown Document" in md_content
            
            html_content = extract_text(str(html_file))
            assert "HTML Document" in html_content
            
            # Test directory extraction
            all_content = extract_text_from_directory(tmp_dir)
            assert len(all_content) == 3
            assert str(txt_file) in all_content
            assert str(md_file) in all_content
            assert str(html_file) in all_content
    
    def test_supported_extensions_coverage(self):
        """Test that all supported extensions are properly handled."""
        extensions = get_supported_extensions()
        
        # Test that we can handle the basic text-based formats
        text_extensions = ['.txt', '.md', '.html']
        for ext in text_extensions:
            assert ext in extensions
        
        # Test that binary formats are included
        binary_extensions = ['.pdf', '.docx', '.doc']
        for ext in binary_extensions:
            assert ext in extensions
