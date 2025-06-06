"""
Command-line interface for metaminer.
"""
import argparse
import sys
import os
from pathlib import Path
from typing import Optional

from .inquiry import Inquiry
from .config import Config


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Extract structured information from documents using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  metaminer questions.txt documents/
  metaminer questions.csv document.pdf --output results.json
  metaminer questions.txt documents/ --format json
        """
    )
    
    parser.add_argument(
        "questions_file",
        help="Path to questions file (.txt or .csv)"
    )
    
    parser.add_argument(
        "documents",
        help="Path to document file or directory containing documents"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: print to stdout)"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)"
    )
    
    parser.add_argument(
        "--model", "-m",
        help="AI model to use (default: gpt-3.5-turbo)"
    )
    
    parser.add_argument(
        "--base-url",
        help="OpenAI API base URL (default: http://localhost:5001/api/v1)"
    )
    
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (can also be set via OPENAI_API_KEY environment variable)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--show-questions",
        action="store_true",
        help="Output the normalized question structure with inferred types and exit"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.questions_file):
        print(f"Error: Questions file not found: {args.questions_file}", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.exists(args.documents):
        print(f"Error: Documents path not found: {args.documents}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Create configuration with CLI arguments
        # None values will fall back to environment variables or defaults
        config = Config(
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key
        )
        
        # Create Inquiry instance
        if args.verbose:
            print(f"Loading questions from: {args.questions_file}", file=sys.stderr)
            print(f"Using model: {config.model}", file=sys.stderr)
            print(f"Using base URL: {config.base_url}", file=sys.stderr)
        
        inquiry = Inquiry.from_file(args.questions_file, config=config)
        
        # If show-questions flag is set, output the normalized questions and exit
        if args.show_questions:
            import pandas as pd
            
            questions_data = []
            for name, data in inquiry.questions.items():
                questions_data.append({
                    'field_name': name,
                    'question': data['question'],
                    'data_type': data.get('type', 'str'),
                    'output_name': data.get('output_name', name)
                })
            
            questions_df = pd.DataFrame(questions_data)
            
            if args.output:
                output_path = Path(args.output)
                if args.format == "csv":
                    questions_df.to_csv(output_path, index=False)
                elif args.format == "json":
                    questions_df.to_json(output_path, orient="records", indent=2)
                
                if args.verbose:
                    print(f"Questions saved to: {output_path}", file=sys.stderr)
            else:
                if args.format == "csv":
                    print(questions_df.to_csv(index=False))
                elif args.format == "json":
                    print(questions_df.to_json(orient="records", indent=2))
            
            return
        
        if args.verbose:
            print(f"Processing documents from: {args.documents}", file=sys.stderr)
            print(f"Questions loaded: {len(inquiry.questions)}", file=sys.stderr)
        
        # Process documents
        results_df = inquiry.process_documents(args.documents)
        
        if results_df.empty:
            print("Warning: No results generated", file=sys.stderr)
            sys.exit(0)
        
        if args.verbose:
            print(f"Processed {len(results_df)} documents", file=sys.stderr)
        
        # Output results
        if args.output:
            output_path = Path(args.output)
            if args.format == "csv":
                results_df.to_csv(output_path, index=False)
            elif args.format == "json":
                results_df.to_json(output_path, orient="records", indent=2)
            
            if args.verbose:
                print(f"Results saved to: {output_path}", file=sys.stderr)
        else:
            # Print to stdout
            if args.format == "csv":
                print(results_df.to_csv(index=False))
            elif args.format == "json":
                print(results_df.to_json(orient="records", indent=2))
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
