import pandas as pd
import os
import openai
from typing import Union, List
from .inquiry import Inquiry

def extract_metadata(inquiry: Inquiry, documents: Union[str, List[str]] = None) -> pd.DataFrame:
    """
    Extract metadata from documents using an Inquiry instance.
    
    This function is maintained for backward compatibility.
    For new code, use inquiry.process_documents() directly.
    
    Args:
        inquiry: Inquiry instance with questions defined
        documents: Document path(s) to process (optional, for compatibility)
        
    Returns:
        pd.DataFrame: Extracted metadata
    """
    if documents is not None:
        # New behavior: process the provided documents
        return inquiry.process_documents(documents)
    else:
        # Legacy behavior: return empty DataFrame with question columns
        if not inquiry.questions:
            return pd.DataFrame()
        
        # Create empty DataFrame with columns based on questions
        columns = []
        for field_name, question_data in inquiry.questions.items():
            output_name = question_data.get("output_name", field_name)
            columns.append(output_name)
        
        # Add metadata columns
        columns.extend(["_document_path", "_document_name"])
        
        return pd.DataFrame(columns=columns)
