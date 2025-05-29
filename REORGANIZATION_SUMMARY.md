# Metaminer Reorganization Summary

## Task Completed Successfully ✅

The metaminer codebase has been successfully reorganized to work both as a Python module and a command-line utility, exactly as requested.

## New Usage Patterns

### Command Line Interface
```bash
# Basic usage as requested
metaminer questions.txt documents/

# Additional options
metaminer questions.csv document.pdf --output results.json
metaminer questions.txt documents/ --format json --verbose
```

### Python Module Usage
```python
from metaminer import Inquiry

# From question file
inquiry = Inquiry.from_file("questions.txt")
df = inquiry.process_documents("documents/")

# Direct questions
inquiry = Inquiry(questions=["Who is the author?", "What is the publication date?"])
df = inquiry.process_documents(["doc1.pdf", "doc2.docx"])
```

## New Architecture

### File Structure
```
metaminer/
├── __init__.py          # Main exports
├── inquiry.py           # Enhanced Inquiry class with Pydantic schemas
├── document_reader.py   # Pandoc-based document text extraction
├── question_parser.py   # Parse questions from TXT/CSV files
├── schema_builder.py    # Dynamic Pydantic schema generation
├── cli.py              # Command-line interface
├── extractor.py        # Updated for backward compatibility
└── __main__.py         # Enable `python -m metaminer`
```

### Key Features Added

1. **Document Format Support** (via pandoc)
   - PDF, DOCX, ODT, RTF, TXT, MD, HTML, EPUB, LaTeX
   - Automatic format detection and text extraction

2. **Question File Formats**
   - **Text files (.txt)**: One question per line
   - **CSV files (.csv)**: Structured with field names and data types

3. **Dynamic Pydantic Schemas**
   - Automatically generated from questions
   - Type validation (str, int, float, bool, date)
   - Structured output validation

4. **Command-Line Interface**
   - Console script entry point: `metaminer`
   - Module execution: `python -m metaminer`
   - Multiple output formats (CSV, JSON)
   - Configurable API endpoints

5. **Enhanced API Integration**
   - Default endpoint: `http://localhost:5001/api/v1`
   - Auto-detection of available models
   - Structured JSON output requests
   - Error handling and validation

## Configuration

### API Settings
- **Default base URL**: `http://localhost:5001/api/v1` (as requested)
- **Model selection**: Automatically queries `/models` endpoint
- **API key**: Via environment variable or command-line option

### Output Formats
- **CLI default**: CSV (as requested)
- **Python module**: pandas DataFrame (as requested)
- **Alternative**: JSON format available

## Dependencies Added
- `pypandoc>=1.5` - Document processing via pandoc
- Enhanced `pydantic>=2.0.0` usage for dynamic schemas
- Maintained existing dependencies (openai, pandas)

## Backward Compatibility
- Existing `Inquiry` class API preserved
- `extract_metadata()` function updated but compatible
- All existing tests should continue to work

## Installation & Setup
```bash
# Install the package
pip install -e .

# Install system dependency
sudo apt-get install pandoc  # Ubuntu/Debian
brew install pandoc          # macOS

# Test functionality
python test_metaminer.py
```

## Example Files Created
- `example_questions.txt` - Simple text format
- `example_questions.csv` - Structured CSV format  
- `example_document.txt` - Sample document for testing
- `test_metaminer.py` - Comprehensive functionality test

## Verification Results ✅
- ✅ Question parsing (TXT and CSV formats)
- ✅ Document text extraction (via pandoc)
- ✅ Dynamic Pydantic schema generation
- ✅ LLM prompt generation
- ✅ Command-line interface (`metaminer` command)
- ✅ Module execution (`python -m metaminer`)
- ✅ Python module imports
- ✅ Package installation with console script
- ✅ Backward compatibility maintained

## Ready for Use
The metaminer package is now ready to be used exactly as specified:
```bash
metaminer questions.txt documents/
```

Where:
- `questions.txt` contains questions (one per line)
- `documents/` is a directory containing PDF, DOCX, TXT, or other supported document files
- Output will be CSV format by default, with pandas DataFrame when used as Python module
- API will connect to `localhost:5001/api/v1` by default and auto-detect the model
