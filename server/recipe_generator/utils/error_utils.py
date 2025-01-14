import json
from datetime import datetime
from pathlib import Path
from typing import Optional

def save_error_to_file(error_data: dict, prefix: Optional[str] = "error") -> None:
    """Save error data to a JSON file.
    
    Args:
        error_data: Dictionary containing error information
        prefix: Optional prefix for the error file name (default: "error")
    """
    if not error_data:
        print("Warning: Empty error data, nothing to save")
        return
        
    try:
        # Create errors directory if it doesn't exist
        errors_dir = Path(__file__).parent.parent.parent / "data" / "errors"
        errors_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")
        error_file = errors_dir / f"{prefix}_{timestamp}.json"
        
        # Add timestamp and ensure we have an error type
        error_data["timestamp"] = datetime.now().isoformat()
        if "error_type" not in error_data:
            error_data["error_type"] = "unknown"
        
        # Save to file
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(error_data, f, indent=2, ensure_ascii=False)
            
        print(f"Error data saved to: {error_file}")
        
    except Exception as e:
        print(f"Failed to save error data: {str(e)}")
        print("Error data:", error_data)