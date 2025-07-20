import json
import os
from typing import Dict, Any, Optional
import openai
from dotenv import load_dotenv

try:
    from google.cloud import secretmanager
    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    SECRET_MANAGER_AVAILABLE = False

"""
Processing agent module for converting JSON to Markdown using OpenAI.
"""


class ProcessingAgent:
    """
    Agent that processes JSON data and converts it to markdown format
    using OpenAI's GPT models.
    """
    def __init__(self):
        """Initialize the processing agent with API credentials."""
        load_dotenv()
        
        # Get OpenAI API key from Secret Manager or environment
        openai_api_key = self._get_secret("openai-api-key")
        if not openai_api_key:
            print("Warning: OPENAI_API_KEY not found. Using fallback markdown conversion.")
            self.client = None
            self.model = None
        else:
            self.client = openai.OpenAI(api_key=openai_api_key)
            self.model = "gpt-4o-mini"  # Updated to correct model name

    def _get_secret(self, secret_name: str) -> Optional[str]:
        """
        Get secret from Google Secret Manager or fall back to environment variables.
        
        Args:
            secret_name: Name of the secret in Secret Manager
            
        Returns:
            Secret value or None if not found
        """
        # Try Secret Manager first (for production)
        if SECRET_MANAGER_AVAILABLE:
            try:
                project_id = os.getenv("GCP_PROJECT_ID")
                if project_id:
                    client = secretmanager.SecretManagerServiceClient()
                    secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                    response = client.access_secret_version(request={"name": secret_path})
                    return response.payload.data.decode("UTF-8")
            except Exception as e:
                print(f"Failed to get secret from Secret Manager: {e}")
        
        # Fall back to environment variables (for local development)
        env_name = secret_name.upper().replace("-", "_")
        return os.getenv(env_name)


    def json_to_markdown(self, json_data: Dict[str, Any], 
                          custom_instructions: Optional[str] = None) -> str:
        """
        Convert JSON data to a nicely formatted markdown.
        
        Args:
            json_data: Dictionary containing the JSON data to convert
            custom_instructions: Optional specific formatting instructions
            
        Returns:
            Formatted markdown string
        """
        # If no OpenAI client, return helpful message instead of fallback
        if not self.client:
            return """
# ⚠️ OpenAI Integration Not Available

The OpenAI API integration is not configured properly. This could be due to:

- Missing API key in environment variables or Google Secret Manager
- Incorrect secret name in Secret Manager
- Network connectivity issues

**Raw Data:**
```json
{}
```

To fix this, ensure:
1. Your OpenAI API key is properly set in the environment
2. For production: The secret `openai-api-key` exists in Google Secret Manager
3. For local development: The `OPENAI_API_KEY` is set in your `.env` file
""".format(json.dumps(json_data, indent=2))
        
        # Prepare JSON as a string
        json_str = json.dumps(json_data, indent=2)
        
        # Build the prompt
        instruction = (
            custom_instructions or 
            "Convert the following JSON data to a well-structured, readable Markdown format. "
            "Use appropriate markdown features like headers, lists, tables, code blocks, etc. "
            "Make it visually appealing and easy to read."
        )
        
        
        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": json_str}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            # Extract and return the markdown content
            return response.choices[0].message.content
            
        except Exception as e:
            return f"""
# ❌ OpenAI API Error

Failed to process data with OpenAI API: {str(e)}

This might be due to:
- API rate limits or quota exceeded
- Network connectivity issues
- Invalid API key or model access

**Raw Data:**
```json
{json.dumps(json_data, indent=2)}
```

Please check your OpenAI API configuration and try again.
"""

    def process_file(self, input_file_path: str, output_file_path: str, 
                     custom_instructions: Optional[str] = None) -> bool:
        """
        Process a JSON file and write the markdown output to a file.
        
        Args:
            input_file_path: Path to the input JSON file
            output_file_path: Path where the markdown will be saved
            custom_instructions: Optional specific formatting instructions
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read JSON from file
            with open(input_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Convert to markdown
            markdown = self.json_to_markdown(json_data, custom_instructions)
            
            # Write to output file
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
                
            return True
            
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            return False