import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, mock_open
from dash_mcp_showcase.processing_agent import ProcessingAgent


class TestProcessingAgent:
    """Test cases for the ProcessingAgent class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.sample_json = {
            "name": "Test Report",
            "data": [
                {"id": 1, "value": 100},
                {"id": 2, "value": 200}
            ],
            "summary": "Sample data for testing"
        }

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"})
    @patch('dash_mcp_showcase.processing_agent.openai.OpenAI')
    def test_init_with_api_key(self, mock_openai):
        """Test successful initialization with API key from environment."""
        agent = ProcessingAgent()
        
        assert agent.client is not None
        assert agent.model == "gpt-4o-mini"
        mock_openai.assert_called_once_with(api_key="test-key-123")

    @patch('dash_mcp_showcase.processing_agent.ProcessingAgent._get_secret')
    def test_init_without_api_key(self, mock_get_secret):
        """Test initialization without API key (fallback mode)."""
        # Mock _get_secret to return None (no API key found)
        mock_get_secret.return_value = None
        
        agent = ProcessingAgent()
        
        assert agent.client is None
        assert agent.model is None
        mock_get_secret.assert_called_once_with("openai-api-key")

    @patch('dash_mcp_showcase.processing_agent.SECRET_MANAGER_AVAILABLE', True)
    @patch('dash_mcp_showcase.processing_agent.secretmanager.SecretManagerServiceClient')
    @patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"})
    def test_get_secret_from_secret_manager(self, mock_sm_client):
        """Test getting secret from Google Secret Manager."""
        # Mock the Secret Manager response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.payload.data.decode.return_value = "secret-api-key"
        mock_client.access_secret_version.return_value = mock_response
        mock_sm_client.return_value = mock_client
        
        # Create agent without calling __init__ to avoid double calls
        agent = ProcessingAgent.__new__(ProcessingAgent)
        result = agent._get_secret("openai-api-key")
        
        assert result == "secret-api-key"
        mock_client.access_secret_version.assert_called_once()

    @patch('dash_mcp_showcase.processing_agent.SECRET_MANAGER_AVAILABLE', True)
    @patch('dash_mcp_showcase.processing_agent.secretmanager.SecretManagerServiceClient')
    @patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project", "OPENAI_API_KEY": "fallback-key"})
    def test_get_secret_fallback_to_env(self, mock_sm_client):
        """Test fallback to environment variable when Secret Manager fails."""
        # Make Secret Manager raise an exception
        mock_sm_client.side_effect = Exception("Secret Manager error")
        
        # Create agent without calling __init__ to test _get_secret in isolation
        agent = ProcessingAgent.__new__(ProcessingAgent)
        result = agent._get_secret("openai-api-key")
        
        assert result == "fallback-key"

    @patch.dict(os.environ, {}, clear=True)
    @patch('dash_mcp_showcase.processing_agent.SECRET_MANAGER_AVAILABLE', False)
    def test_get_secret_not_found(self):
        """Test when secret is not found anywhere."""
        # Create agent without triggering __init__ patching issues
        agent = ProcessingAgent.__new__(ProcessingAgent)  # Create without calling __init__
        result = agent._get_secret("nonexistent-secret")
        
        assert result is None

    @patch.dict(os.environ, {"TEST_SECRET": "test-value"}, clear=True)
    @patch('dash_mcp_showcase.processing_agent.SECRET_MANAGER_AVAILABLE', False)
    def test_get_secret_from_env_direct(self):
        """Test getting secret from environment variables directly."""
        agent = ProcessingAgent.__new__(ProcessingAgent)  # Create without calling __init__
        result = agent._get_secret("test-secret")  # Should look for TEST_SECRET
        
        assert result == "test-value"

    def test_json_to_markdown_without_client(self):
        """Test markdown conversion when OpenAI client is not available."""
        agent = ProcessingAgent()
        agent.client = None  # Simulate no API key
        
        result = agent.json_to_markdown(self.sample_json)
        
        assert "⚠️ OpenAI Integration Not Available" in result
        assert "Raw Data:" in result
        assert json.dumps(self.sample_json, indent=2) in result

    @patch('dash_mcp_showcase.processing_agent.openai.OpenAI')
    def test_json_to_markdown_success(self, mock_openai):
        """Test successful JSON to markdown conversion."""
        # Mock the OpenAI response with proper structure
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "# Test Report\n\nConverted markdown content"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]  # Use list instead of trying to subscript Mock
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            agent = ProcessingAgent()
            result = agent.json_to_markdown(self.sample_json)
        
        assert result == "# Test Report\n\nConverted markdown content"
        mock_client.chat.completions.create.assert_called_once()

    @patch('dash_mcp_showcase.processing_agent.openai.OpenAI')
    def test_json_to_markdown_with_custom_instructions(self, mock_openai):
        """Test JSON to markdown conversion with custom instructions."""
        # Mock the OpenAI response with proper structure
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Custom formatted content"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]  # Use list instead of trying to subscript Mock
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            agent = ProcessingAgent()
            custom_instructions = "Format this as a table with specific headers"
            result = agent.json_to_markdown(self.sample_json, custom_instructions)
        
        assert result == "Custom formatted content"
        # Check that custom instructions were used in the API call
        call_args = mock_client.chat.completions.create.call_args
        assert custom_instructions in call_args[1]['messages'][0]['content']

    @patch('dash_mcp_showcase.processing_agent.openai.OpenAI')
    def test_json_to_markdown_api_error(self, mock_openai):
        """Test handling of OpenAI API errors."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API rate limit exceeded")
        mock_openai.return_value = mock_client
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            agent = ProcessingAgent()
            result = agent.json_to_markdown(self.sample_json)
        
        assert "❌ OpenAI API Error" in result
        assert "API rate limit exceeded" in result
        assert "Raw Data:" in result

    def test_process_file_success(self):
        """Test successful file processing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as input_file:
            json.dump(self.sample_json, input_file)
            input_path = input_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as output_file:
            output_path = output_file.name
        
        try:
            agent = ProcessingAgent()
            agent.client = None  # Use fallback mode for predictable output
            
            result = agent.process_file(input_path, output_path)
            
            assert result is True
            
            # Check that output file was created and contains expected content
            with open(output_path, 'r') as f:
                content = f.read()
                assert "⚠️ OpenAI Integration Not Available" in content
        
        finally:
            os.unlink(input_path)
            os.unlink(output_path)

    def test_process_file_invalid_json(self):
        """Test file processing with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as input_file:
            input_file.write("invalid json content {")
            input_path = input_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as output_file:
            output_path = output_file.name
        
        try:
            agent = ProcessingAgent()
            result = agent.process_file(input_path, output_path)
            
            assert result is False
        
        finally:
            os.unlink(input_path)
            os.unlink(output_path)

    def test_process_file_nonexistent_input(self):
        """Test file processing with nonexistent input file."""
        agent = ProcessingAgent()
        result = agent.process_file("nonexistent.json", "output.md")
        
        assert result is False

    @patch("builtins.open", mock_open(read_data='{"test": "data"}'))
    def test_process_file_write_error(self):
        """Test file processing with write permission error."""
        agent = ProcessingAgent()
        
        # Mock the write operation to raise an exception
        with patch("builtins.open", mock_open(read_data='{"test": "data"}')) as mock_file:
            mock_file.return_value.__enter__.return_value.write.side_effect = PermissionError("Permission denied")
            
            result = agent.process_file("test.json", "/root/readonly.md")
            assert result is False

    def test_empty_json_handling(self):
        """Test handling of empty JSON data."""
        agent = ProcessingAgent()
        agent.client = None  # Use fallback mode
        
        result = agent.json_to_markdown({})
        
        assert "⚠️ OpenAI Integration Not Available" in result
        assert "{}" in result

    def test_complex_nested_json(self):
        """Test handling of complex nested JSON structures."""
        complex_json = {
            "users": [
                {
                    "id": 1,
                    "profile": {
                        "name": "John Doe",
                        "settings": {
                            "theme": "dark",
                            "notifications": True
                        }
                    }
                }
            ],
            "metadata": {
                "version": "1.0",
                "created": "2025-01-01"
            }
        }
        
        agent = ProcessingAgent()
        agent.client = None  # Use fallback mode
        
        result = agent.json_to_markdown(complex_json)
        
        assert "⚠️ OpenAI Integration Not Available" in result
        # Should contain the formatted JSON
        assert '"users"' in result
        assert '"profile"' in result


# Integration tests (require actual API key - run separately)
class TestProcessingAgentIntegration:
    """Integration tests that require actual OpenAI API access."""
    
    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No OpenAI API key available")
    def test_real_api_call(self):
        """Test with real OpenAI API call (requires valid API key)."""
        agent = ProcessingAgent()
        
        if agent.client is None:
            pytest.skip("OpenAI client not available")
        
        simple_json = {"title": "Test", "value": 42}
        result = agent.json_to_markdown(simple_json)
        
        # Should return actual markdown, not error message
        assert "❌ OpenAI API Error" not in result
        assert "⚠️ OpenAI Integration Not Available" not in result
        assert len(result.strip()) > 0


if __name__ == "__main__":
    pytest.main([__file__])
