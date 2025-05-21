import os
from typing import Optional
import logging
import openai
from google.generativeai import GenerativeModel
import google.generativeai as genai

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMService:
    """
    Service for interacting with different LLM providers (OpenAI and Google Gemini).
    """

    def __init__(self):
        """Initialize the LLM service based on environment configuration."""
        providers_str = os.getenv("LLM_PROVIDER", "google").lower()
        self.available_providers = [p.strip() for p in providers_str.split(",") if p.strip()]

        # If no providers are specified, default to Google
        if not self.available_providers:
            self.available_providers = ["google"]

        self.provider = self.available_providers[0]

        logger.info(f"Initializing LLM service with available providers: {self.available_providers}")
        logger.info(f"Default provider: {self.provider}")

        # Initialize OpenAI if needed
        if "openai" in self.available_providers:
            logger.info("Configuring OpenAI provider")
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                logger.error("OPENAI_API_KEY environment variable is missing")
                raise ValueError("OPENAI_API_KEY environment variable is required when using OpenAI provider")
            openai.api_key = openai_api_key
            logger.info("OpenAI provider configured successfully")

        # Initialize Google Gemini if needed
        if "google" in self.available_providers:
            logger.info("Configuring Google Gemini provider")
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                logger.error("GOOGLE_API_KEY environment variable is missing")
                raise ValueError("GOOGLE_API_KEY environment variable is required when using Google provider")
            genai.configure(api_key=google_api_key)
            logger.info("Google Gemini provider configured successfully")

        # Validate that at least one provider is available
        if not self.available_providers:
            logger.error("No LLM providers configured")
            raise ValueError("No LLM providers configured. Use 'openai' or 'google'.")

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

        # Check if the provider is in the available providers list
        if active_provider not in self.available_providers:
            logger.warning(f"Requested provider '{active_provider}' is not in available providers list. Using default provider '{self.provider}' instead.")
            active_provider = self.provider

        # Log prompt length instead of full prompt for privacy and to avoid huge log files
        prompt_length = len(prompt)
        logger.info(f"Generating text with provider: {active_provider}, prompt length: {prompt_length} chars, max_tokens: {max_tokens or 'default'}")

        try:
            if active_provider == "openai":
                result = self._generate_with_openai(prompt, max_tokens)
                logger.info(f"Successfully generated text with OpenAI, response length: {len(result)} chars")
                return result
            elif active_provider == "google":
                result = self._generate_with_gemini(prompt, max_tokens)
                logger.info(f"Successfully generated text with Google Gemini, response length: {len(result)} chars")
                return result
            else:
                logger.error(f"Unsupported LLM provider: {active_provider}")
                raise ValueError(f"Unsupported LLM provider: {active_provider}")
        except Exception as e:
            logger.error(f"Error generating text with {active_provider}: {str(e)}")
            raise

    def _generate_with_openai(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate text using OpenAI's API."""
        logger.debug("Attempting to generate text with OpenAI")
        try:
            # Try with the newer client API first
            try:
                logger.debug("Using new OpenAI client API")
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                logger.info("Sending request to OpenAI API (gpt-4o-mini)")
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful financial analyst assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens
                )
                logger.info("Received response from OpenAI API")
                return response.choices[0].message.content
            except ImportError:
                # Fall back to legacy API if the new client is not available
                logger.info("New OpenAI client not available, falling back to legacy API")
                logger.info("Sending request to OpenAI API (legacy, gpt-4o-mini)")
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful financial analyst assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens
                )
                logger.info("Received response from OpenAI API (legacy)")
                return response.choices[0].message.content
        except Exception as e:
            # Handle quota exceeded errors
            error_msg = str(e).lower()
            if "quota" in error_msg or "exceeded" in error_msg or "billing" in error_msg:
                logger.error(f"OpenAI API quota exceeded: {str(e)}")
                return "Error: OpenAI API quota exceeded. Please check your billing details or try using a different provider."
            else:
                # Log other errors
                logger.error(f"Error with OpenAI API: {str(e)}")
                # Re-raise other errors
                raise

    def _generate_with_gemini(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate text using Google's Gemini API."""
        logger.debug("Attempting to generate text with Google Gemini")

        # Configure the generation config if max_tokens is provided
        generation_config = None
        if max_tokens:
            generation_config = {"max_output_tokens": max_tokens}
            logger.debug(f"Using custom max_output_tokens: {max_tokens}")
        else:
            logger.debug("Using default max_output_tokens")

        try:
            # Use the correct model name for the API
            model_name = "gemini-1.5-pro"
            logger.info(f"Sending request to Google Gemini API ({model_name})")
            model = GenerativeModel(model_name)
            response = model.generate_content(prompt, generation_config=generation_config)
            logger.info(f"Received response from Google Gemini API ({model_name})")
            return response.text
        except Exception as primary_error:
            logger.warning(f"Error with primary model (gemini-1.5-pro): {str(primary_error)}")
            try:
                # If the model name is not found, try with the alternative model name
                if "not found" in str(primary_error):
                    alternative_model = "gemini-pro"
                    logger.info(f"Primary model not found, trying alternative model: {alternative_model}")
                    model = GenerativeModel(alternative_model)
                    response = model.generate_content(prompt, generation_config=generation_config)
                    logger.info(f"Received response from Google Gemini API ({alternative_model})")
                    return response.text
                else:
                    logger.error(f"Error is not related to model availability: {str(primary_error)}")
                    raise primary_error
            except Exception as e:
                # Handle common error cases with user-friendly messages
                error_str = str(e).lower()

                if "api key" in error_str or "authentication" in error_str:
                    logger.error(f"Google API key authentication error: {str(e)}")
                    return "Error: Invalid or missing Google API key. Please check your API key configuration."
                elif "quota" in error_str or "exceeded" in error_str or "limit" in error_str:
                    logger.error(f"Google API quota exceeded: {str(e)}")
                    return "Error: Google API quota exceeded. Please check your usage limits or try using a different provider."
                elif "not found" in error_str or "unsupported" in error_str:
                    logger.error(f"Google Gemini model not available: {str(e)}")
                    return "Error: The requested Gemini model is not available. Please check your API version or try using a different provider."
                elif "content" in error_str and "blocked" in error_str:
                    logger.warning(f"Content blocked by Google safety filters: {str(e)}")
                    return "Error: The content was blocked by Google's safety filters. Please modify your prompt and try again."
                else:
                    # Log and re-raise other errors
                    logger.error(f"Unexpected error with Google Gemini API: {str(e)}")
                    raise

# Singleton instance for easy import
llm_service = LLMService()
