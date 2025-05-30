# Metaminer

[![Tests](https://github.com/travis4dams/metaminer/workflows/Tests/badge.svg)](https://github.com/travis4dams/metaminer/actions)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

A tool for extracting structured information from documents using AI.

## Overview

Metaminer allows you to extract structured data from various document formats (PDF, DOCX, TXT, etc.) by asking natural language questions. It uses AI to analyze documents and return structured results in CSV or JSON format.

## Installation

```bash
pip install metaminer
```

### System Requirements

Metaminer requires [pandoc](https://pandoc.org/installing.html) to be installed on your system for document processing:

- **Ubuntu/Debian**: `sudo apt-get install pandoc`
- **macOS**: `brew install pandoc`
- **Windows**: Download from [pandoc.org](https://pandoc.org/installing.html)

**Note**: Metaminer uses pandoc for most document formats and PyMuPDF specifically for PDF processing to ensure optimal text extraction.

## Usage

### Command Line Interface

```bash
# Basic usage
metaminer questions.txt documents/

# Process single document
metaminer questions.txt document.pdf

# Save results to file
metaminer questions.txt documents/ --output results.csv

# JSON output format
metaminer questions.txt documents/ --format json --output results.json

# Custom API endpoint
metaminer questions.txt documents/ --base-url http://localhost:8000/api/v1
```

### Python Module

```python
from metaminer import Inquiry, extract_metadata, Config
from metaminer import extract_text, get_supported_extensions
import pandas as pd

# From question file
inquiry = Inquiry.from_file("questions.txt")
df = inquiry.process_documents("documents/")

# Direct questions
inquiry = Inquiry(questions=["Who is the author?", "What is the publication date?"])
df = inquiry.process_documents(["doc1.pdf", "doc2.docx"])

# Single document
result = inquiry.process_document("document.pdf")

# Extract text directly
text = extract_text("document.pdf")

# Get supported file extensions
extensions = get_supported_extensions()

# Use configuration
config = Config()
print(f"Default API endpoint: {config.base_url}")
```

## Question Formats

### Text File (.txt)
One question per line:
```
Who is the author?
What is the publication date?
What is the main topic?
```

### CSV File (.csv)
Structured format with optional field names and data types:
```csv
question,field_name,data_type
"Who is the author?",author,str
"What is the publication date?",pub_date,date
"How many pages?",page_count,int
```

Supported data types:
- `str` (default): Text
- `int`: Integer numbers
- `float`: Decimal numbers
- `bool`: True/False values
- `date`: Date values

## Supported Document Formats

Thanks to pandoc integration and PyMuPDF, metaminer supports:
- PDF (.pdf)
- Microsoft Word (.docx, .doc)
- OpenDocument (.odt)
- Rich Text Format (.rtf)
- Plain text (.txt)
- Markdown (.md)
- HTML (.html)
- EPUB (.epub)
- LaTeX (.tex)

## Configuration

### API Settings

By default, metaminer connects to a local AI server at `http://localhost:5001/api/v1`. You can customize this using environment variables or command-line options:

#### Environment Variables

```bash
# API Configuration
export OPENAI_API_KEY=your-api-key
export METAMINER_BASE_URL=http://your-api-server.com/api/v1
export METAMINER_MODEL=gpt-4
export METAMINER_TIMEOUT=60
export METAMINER_MAX_RETRIES=5

# Logging Configuration
export METAMINER_LOG_LEVEL=DEBUG
```

#### Command Line

```bash
metaminer questions.txt documents/ --base-url http://your-api-server.com/api/v1
```

#### Python

```python
from metaminer import Inquiry, Config

# Using configuration
config = Config()
inquiry = Inquiry.from_file("questions.txt", base_url="http://your-api-server.com/api/v1")

# Or set environment variables before creating Inquiry
import os
os.environ["METAMINER_BASE_URL"] = "http://your-api-server.com/api/v1"
inquiry = Inquiry.from_file("questions.txt")
```

### Configuration Defaults

- **Base URL**: `http://localhost:5001/api/v1`
- **Model**: `gpt-3.5-turbo`
- **Timeout**: 30 seconds
- **Max Retries**: 3
- **Log Level**: INFO
- **Max File Size**: 50MB

## Output Format

Results include the extracted information plus metadata:

```csv
author,pub_date,page_count,_document_path,_document_name
"John Doe","2023-01-15",25,"/path/to/doc1.pdf","doc1.pdf"
"Jane Smith","2023-02-20",18,"/path/to/doc2.pdf","doc2.pdf"
```

## Examples

### Research Paper Analysis
```txt
# questions.txt
Who are the authors?
What is the title?
What journal was this published in?
What is the publication year?
What is the main research question?
What methodology was used?
```

### Invoice Processing
```csv
question,field_name,data_type
"What is the invoice number?",invoice_number,str
"What is the total amount?",total_amount,float
"What is the invoice date?",invoice_date,date
"Who is the vendor?",vendor_name,str
"What is the due date?",due_date,date
```

### Legal Document Review
```txt
What type of document is this?
Who are the parties involved?
What is the effective date?
What is the termination date?
What are the key obligations?
```

## Development

### Running Tests
```bash
pip install -e ".[dev]"
pytest
```

### Project Structure
```
metaminer/
├── __init__.py          # Main exports
├── inquiry.py           # Core Inquiry class
├── document_reader.py   # Document text extraction
├── question_parser.py   # Question file parsing
├── schema_builder.py    # Pydantic schema generation
├── extractor.py         # Metadata extraction utilities
├── config.py           # Configuration management
├── cli.py              # Command-line interface
└── __main__.py         # Module entry point
```

## License

GNU Lesser General Public License v3.0 - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
