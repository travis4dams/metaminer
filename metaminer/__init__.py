from .inquiry import Inquiry
from .extractor import extract_metadata
from .document_reader import extract_text, extract_text_from_directory, get_supported_extensions
from .question_parser import parse_questions_from_file
from .schema_builder import build_schema_from_questions
from .config import Config, setup_logging
from .datatype_inferrer import DataTypeInferrer, TypeSuggestion, infer_question_types

__version__ = "0.3.7rc"

__all__ = [
    "Inquiry",
    "extract_metadata",
    "extract_text",
    "extract_text_from_directory",
    "get_supported_extensions",
    "parse_questions_from_file",
    "build_schema_from_questions",
    "Config",
    "setup_logging",
    "DataTypeInferrer",
    "TypeSuggestion",
    "infer_question_types",
]
