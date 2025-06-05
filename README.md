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

# Custom API endpoint and model
metaminer questions.txt documents/ --base-url http://localhost:8000/api/v1 --model gpt-4

# Use specific AI model
metaminer questions.txt documents/ --model gpt-4

# Show normalized question structure with inferred types
metaminer questions.txt --show-questions --output questions_analysis.csv

# Verbose output for debugging
metaminer questions.txt documents/ --verbose

# Custom API key and model
metaminer questions.txt documents/ --api-key your-api-key --model gpt-4
```

### Python Module

```python
from metaminer import Inquiry, extract_metadata, Config
from metaminer import extract_text, extract_text_from_directory, get_supported_extensions
from metaminer import DataTypeInferrer, infer_question_types, setup_logging
import pandas as pd

# From question file
inquiry = Inquiry.from_file("questions.txt")
df = inquiry.process_documents("documents/")

# Direct questions
inquiry = Inquiry(questions=["Who is the author?", "What is the publication date?"])
df = inquiry.process_documents(["doc1.pdf", "doc2.docx"])

# Single document
result = inquiry.process_document("document.pdf")

# Process text directly (without files)
inquiry = Inquiry(questions=["Who is the author?", "What is the main topic?"])
result = inquiry.process_text("This is a research paper by Dr. Smith about machine learning.")

# Process multiple texts with concurrent processing
texts = ["Document 1 content...", "Document 2 content...", "Document 3 content..."]
results = inquiry.process_texts(texts)  # Uses concurrent processing by default

# Pandas integration for seamless data processing
import pandas as pd
df = pd.DataFrame({'text': ["Doc 1 content", "Doc 2 content", "Doc 3 content"]})

# Method 1: Using apply
df['results'] = df['text'].apply(inquiry.process_text)

# Method 2: Using vectorized processing (better performance for large datasets)
results = inquiry.process_texts(df['text'].tolist())
df['results'] = results

# Extract text directly
text = extract_text("document.pdf")

# Extract text from directory
texts = extract_text_from_directory("documents/")

# Get supported file extensions
extensions = get_supported_extensions()

# Use configuration
config = Config()
print(f"Default API endpoint: {config.base_url}")

# Set up logging
logger = setup_logging(config)

# Infer data types for questions
questions = ["Who is the author?", "What is the publication date?", "How many pages?"]
type_suggestions = infer_question_types(questions)
for q, suggestion in type_suggestions.items():
    print(f"{q}: {suggestion.suggested_type} - {suggestion.reasoning}")

# Use DataTypeInferrer directly
inferrer = DataTypeInferrer()
suggestion = inferrer.infer_single_type("What is the priority level?")
print(f"Suggested type: {suggestion.suggested_type}")
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
Structured format with optional field names, data types, and default values:
```csv
question,field_name,data_type,default
"Who is the author?",author,str,"Unknown"
"What is the publication date?",pub_date,date,
"How many pages?",page_count,int,0
"What is the document type?",doc_type,"enum(report,memo,letter)","report"
```

**CSV Columns:**
- `question` (required): The question to ask about each document
- `field_name` (optional): Custom field name for the output (defaults to auto-generated)
- `data_type` (optional): Data type specification (defaults to `str`)
- `default` (optional): Default value to use when extraction fails or returns empty

Supported data types:
- `str` (default): Text
- `int`: Integer numbers
- `float`: Decimal numbers
- `bool`: True/False values
- `date`: Date values (e.g., YYYY-MM-DD)
- `datetime`: Date and time values (e.g., YYYY-MM-DD HH:MM:SS)
- `list(type)`: Arrays of values (e.g., `list(str)`, `list(int)`, `list(date)`)
- `enum(val1,val2,val3)`: Single choice from discrete values
- `multi_enum(val1,val2,val3)`: Multiple choices from discrete values

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

## Concurrent Processing & Performance

Metaminer includes built-in concurrent processing capabilities for efficient batch processing of multiple texts while respecting API rate limits and system resources.


### Performance Configuration

```python
# For high-throughput processing
config = Config(
    max_concurrent_requests=10,  # More workers for faster processing
    requests_per_minute=300,     # Higher rate limit if your API supports it
    batch_size=100              # Larger batches for better memory efficiency
)

# For rate-limited APIs
config = Config(
    max_concurrent_requests=2,   # Fewer workers to stay under limits
    requests_per_minute=60,      # Conservative rate limit
    batch_size=20               # Smaller batches to reduce memory usage
)
```

### Environment Variables

```bash
# Concurrent processing settings
export METAMINER_MAX_CONCURRENT_REQUESTS=5
export METAMINER_REQUESTS_PER_MINUTE=120
export METAMINER_BATCH_SIZE=50
```

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

# Create Config with explicit parameters
config = Config(
    model="gpt-4",
    base_url="https://api.openai.com/v1",
    api_key="your-api-key"
)
inquiry = Inquiry.from_file("questions.txt", config=config)

# Or use individual parameters
config = Config(model="gpt-4")
inquiry = Inquiry.from_file("questions.txt", config=config)

# Or set environment variables before creating Config
import os
os.environ["METAMINER_BASE_URL"] = "http://your-api-server.com/api/v1"
os.environ["METAMINER_MODEL"] = "gpt-4"
config = Config()  # Will use environment variables
inquiry = Inquiry.from_file("questions.txt", config=config)
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

### Default Value Handling

When extraction fails or returns empty values, default values (if specified) are used:

```csv
author,doc_type,priority,_document_path,_document_name
"John Doe","report","high","/path/to/doc1.pdf","doc1.pdf"
"Unknown","report","medium","/path/to/doc2.pdf","doc2.pdf"
```

In this example, the second document had no extractable author, so the default "Unknown" was used.

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
question,field_name,data_type,default
"What is the invoice number?",invoice_number,str,"N/A"
"What is the total amount?",total_amount,float,0.0
"What is the invoice date?",invoice_date,date,
"Who is the vendor?",vendor_name,str,"Unknown Vendor"
"What is the due date?",due_date,date,
```

### Legal Document Review
```txt
What type of document is this?
Who are the parties involved?
What is the effective date?
What is the termination date?
What are the key obligations?
```

### Document Classification with Enums and Defaults
```csv
question,field_name,data_type,default
"What is the document type?",doc_type,"enum(report,memo,letter,invoice)","report"
"What topics are covered?",topics,"multi_enum(finance,hr,marketing,operations)","finance"
"What is the priority level?",priority,"enum(low,medium,high,urgent)","medium"
"What is the title?",title,str,"Untitled Document"
"Who is the author?",author,str,"Unknown"
```

**Notes**: 
- When using enum types in CSV files, quote the entire type specification to prevent CSV parsing issues with commas
- Default values for enums must be valid enum options
- For multi-enum types, defaults can be single values or comma-separated lists

## Data Type Inference

Metaminer includes an intelligent data type inference system that can automatically suggest appropriate data types for your questions. This feature uses AI to analyze question content and recommend the most suitable data types.

### Using Type Inference

```python
from metaminer import DataTypeInferrer, infer_question_types

# Infer types for multiple questions
questions = [
    "Who is the author?",
    "What is the publication date?", 
    "How many pages are there?",
    "Is this document confidential?",
    "What is the priority level?"
]

type_suggestions = infer_question_types(questions)
for question_id, suggestion in type_suggestions.items():
    print(f"Question: {questions[int(question_id.split('_')[1])-1]}")
    print(f"Suggested type: {suggestion.suggested_type}")
    print(f"Reasoning: {suggestion.reasoning}")
    print(f"Alternatives: {suggestion.alternatives}")
    print()
```

### CLI Type Analysis

You can also analyze your questions from the command line:

```bash
# Analyze questions and show suggested types
metaminer questions.txt --show-questions

# Save analysis to file
metaminer questions.txt --show-questions --output question_analysis.csv
```

This will output a structured analysis showing:
- Original questions
- Suggested data types
- Field names
- Reasoning for type suggestions

### Type Inference Features

- **Smart Analysis**: Uses AI to understand question context and intent
- **Fallback Logic**: Provides sensible defaults when AI analysis fails
- **Validation**: Ensures all suggested types are valid metaminer data types
- **Multiple Suggestions**: Provides alternative type options
- **Reasoning**: Explains why each type was suggested

## Development

### Running Tests
```bash
pip install -e ".[dev]"
pytest
```

### Test Coverage
The project includes comprehensive tests covering:
- Core functionality (document processing, question parsing)
- Data type validation and inference
- Error handling and edge cases
- CSV parsing with various formats
- Default value handling
- Date/datetime processing
- Enum type validation
- Text processing capabilities

### Project Structure
```
metaminer/
├── __init__.py          # Main exports
├── inquiry.py           # Core Inquiry class
├── document_reader.py   # Document text extraction
├── question_parser.py   # Question file parsing
├── schema_builder.py    # Pydantic schema generation
├── datatype_inferrer.py # AI-powered data type inference
├── extractor.py         # Metadata extraction utilities
├── config.py           # Configuration management
├── cli.py              # Command-line interface
└── __main__.py         # Module entry point
```

## License

GNU Lesser General Public License v3.0 - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
