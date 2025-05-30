"""
Document reader module for extracting text from various document formats using pandoc and PyMuPDF.
"""
import os
import pypandoc
from typing import List, Union
from pathlib import Path

import pymupdf  # PyMuPDF


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from PDF files using PyMuPDF.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        str: Extracted text content
        
    Raises:
        RuntimeError: If PyMuPDF is not installed or extraction fails
    """
    if pymupdf is None:
        raise RuntimeError(
            "PyMuPDF is not installed. Please install it: pip install PyMuPDF"
        )
    
    try:
        doc = pymupdf.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF {file_path}: {e}")


def extract_text(file_path: str) -> str:
    """
    Extract text from various document formats using appropriate extractors.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        str: Extracted text content
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        RuntimeError: If extraction fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Route PDF files to PyMuPDF extractor
    if file_path.lower().endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    
    try:
        # Use pandoc for other document formats
        return pypandoc.convert_file(file_path, 'plain')
    except OSError as e:
        if "pandoc" in str(e).lower():
            raise RuntimeError(
                "Pandoc is not installed. Please install pandoc: "
                "https://pandoc.org/installing.html"
            )
        raise
    except Exception as e:
        # Fallback for plain text files
        if file_path.lower().endswith('.txt'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
        raise RuntimeError(f"Failed to extract text from {file_path}: {e}")


def extract_text_from_directory(directory_path: str, extensions: List[str] = None) -> dict:
    """
    Extract text from all supported documents in a directory.
    
    Args:
        directory_path: Path to the directory containing documents
        extensions: List of file extensions to process (default: common document formats)
        
    Returns:
        dict: Mapping of file paths to extracted text content
    """
    if extensions is None:
        extensions = ['.pdf', '.docx', '.doc', '.odt', '.rtf', '.txt', '.md', '.html', '.epub']
    
    directory = Path(directory_path)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory_path}")
    
    results = {}
    
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            try:
                text = extract_text(str(file_path))
                results[str(file_path)] = text
            except Exception as e:
                print(f"Warning: Failed to process {file_path}: {e}")
                continue
    
    return results


def get_supported_extensions() -> List[str]:
    """
    Get list of supported file extensions.
    
    Returns:
        List[str]: List of supported file extensions
    """
    return ['.pdf', '.docx', '.doc', '.odt', '.rtf', '.txt', '.md', '.html', '.epub', '.tex']
