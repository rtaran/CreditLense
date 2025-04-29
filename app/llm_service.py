import os
from typing import Optional
import openai
from google.generativeai import GenerativeModel
import google.generativeai as genai

class LLMService:
    """
    Service for interacting with different LLM providers (OpenAI and Google Gemini).
    """

    def __init__(self):
        """Initialize the LLM service based on environment configuration."""
        self.provider = os.getenv("LLM_PROVIDER", "google").lower()

        # Initialize OpenAI if needed
        if self.provider == "openai":
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required when using OpenAI provider")
            openai.api_key = openai_api_key

        # Initialize Google Gemini if needed
        elif self.provider == "google":
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                raise ValueError("GOOGLE_API_KEY environment variable is required when using Google provider")
            genai.configure(api_key=google_api_key)

        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}. Use 'openai' or 'google'.")

    def generate_text(self, prompt: str, max_tokens: Optional[int] = None, provider: Optional[str] = None) -> str:
        """
        Generate text using the specified or configured LLM provider.

        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum number of tokens to generate (optional)
            provider: The LLM provider to use (optional, defaults to the configured provider)

        Returns:
            The generated text response
        """
        # Use the specified provider if provided, otherwise use the configured provider
        active_provider = provider.lower() if provider else self.provider

        if active_provider == "openai":
            return self._generate_with_openai(prompt, max_tokens)
        elif active_provider == "google":
            return self._generate_with_gemini(prompt, max_tokens)
        else:
            raise ValueError(f"Unsupported LLM provider: {active_provider}")

    def _generate_with_openai(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate text using OpenAI's API."""
        try:
            # Try with the newer client API first
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful financial analyst assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
            except ImportError:
                # Fall back to legacy API if the new client is not available
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful financial analyst assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
        except Exception as e:
            # Handle quota exceeded errors
            if "quota" in str(e).lower() or "exceeded" in str(e).lower() or "billing" in str(e).lower():
                return "Error: OpenAI API quota exceeded. Please check your billing details or try using a different provider."
            else:
                # Re-raise other errors
                raise

    def _generate_with_gemini(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate text using Google's Gemini API."""
        # Configure the generation config if max_tokens is provided
        generation_config = None
        if max_tokens:
            generation_config = {"max_output_tokens": max_tokens}

        try:
            # Use the correct model name for the API
            model = GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(prompt, generation_config=generation_config)
            return response.text
        except Exception as primary_error:
            try:
                # If the model name is not found, try with the alternative model name
                if "not found" in str(primary_error):
                    model = GenerativeModel("gemini-pro")
                    response = model.generate_content(prompt, generation_config=generation_config)
                    return response.text
                else:
                    raise primary_error
            except Exception as e:
                # Handle common error cases with user-friendly messages
                error_str = str(e).lower()

                if "api key" in error_str or "authentication" in error_str:
                    return "Error: Invalid or missing Google API key. Please check your API key configuration."
                elif "quota" in error_str or "exceeded" in error_str or "limit" in error_str:
                    return "Error: Google API quota exceeded. Please check your usage limits or try using a different provider."
                elif "not found" in error_str or "unsupported" in error_str:
                    return "Error: The requested Gemini model is not available. Please check your API version or try using a different provider."
                elif "content" in error_str and "blocked" in error_str:
                    return "Error: The content was blocked by Google's safety filters. Please modify your prompt and try again."
                else:
                    # Re-raise other errors
                    raise

# Singleton instance for easy import
llm_service = LLMService()
