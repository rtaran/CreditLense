import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy.orm import Session

from app.models import (
    CompanyData, 
    FinancialYear, 
    BalanceSheetItem, 
    IncomeStatementItem, 
    CashFlowItem, 
    FinancialRatio
)
from app.llm_service import llm_service

logger = logging.getLogger(__name__)

class FinancialDataExtractor:
    """
    Extracts financial data from PDF text using various methods.
    """

    def __init__(self, pdf_text: str):
        """
        Initialize the extractor with the PDF text.

        Args:
            pdf_text: The text content of the PDF
        """
        self.pdf_text = pdf_text
        self.years = []
        self.balance_sheet_data = {}
        self.income_statement_data = {}
        self.cash_flow_data = {}
        self.ratios = {}

    def extract_data_with_llm(self, provider: str = None) -> Dict[str, Any]:
        """
        Extract financial data from the PDF text using an LLM.

        Args:
            provider: The LLM provider to use (optional)

        Returns:
            A dictionary containing all extracted financial data
        """
        logger.info("Starting extraction of financial data using LLM")

        # Create a prompt for the LLM using the improved method
        logger.info("Creating improved extraction prompt for LLM")
        prompt = self._create_improved_extraction_prompt()

        # Log a sample of the PDF text to help with debugging
        text_sample = self.pdf_text[:500] + "..." if len(self.pdf_text) > 500 else self.pdf_text
        logger.debug(f"PDF text sample for extraction: {text_sample}")
    
        # Generate the financial data using the LLM service
        logger.info(f"Sending prompt to LLM using {provider or 'default'} provider")
        try:
            response = llm_service.generate_text(prompt, provider=provider)
            logger.info(f"Received response from LLM with length {len(response)} characters")
            # Log a sample of the response for debugging
            response_sample = response[:500] + "..." if len(response) > 500 else response
            logger.debug(f"LLM response sample: {response_sample}")
        except Exception as e:
            logger.error(f"Error generating financial data with LLM: {str(e)}")
            # Fall back to regex-based extraction if LLM fails
            logger.info("Falling back to regex-based extraction")
            return self.extract_all_data()

        # Parse the LLM's response to extract the financial data using improved parser
        logger.info("Parsing LLM response to extract financial data")
        try:
            financial_data = self._improved_parse_llm_response(response)

            # Validate the extracted data
            if self._validate_financial_data(financial_data):
                logger.info(f"Successfully parsed and validated financial data from LLM response")
                return financial_data
            else:
                logger.warning("Extracted financial data failed validation")
                # Try one more time with a different provider if available
                if provider != "openai" and "openai" in llm_service.available_providers:
                    logger.info("Attempting extraction with OpenAI as fallback")
                    return self.extract_data_with_llm(provider="openai")
                # Fall back to regex-based extraction if validation fails
                logger.info("Falling back to regex-based extraction")
                return self.extract_all_data()
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            # Fall back to regex-based extraction if parsing fails
            logger.info("Falling back to regex-based extraction")
            return self.extract_all_data()

    def _create_extraction_prompt(self, pdf_text: str) -> str:
        """
        Create a prompt for the LLM to extract financial data.

        This method is kept for backward compatibility.
        New code should use _create_improved_extraction_prompt instead.

        Args:
            pdf_text: The text content of the PDF

        Returns:
            A prompt for the LLM
        """
        # Call the improved prompt method instead
        return self._create_improved_extraction_prompt()

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM's response to extract the financial data.

        Args:
            response: The LLM's response

        Returns:
            A dictionary containing the extracted financial data
        """
        # Try to extract JSON from the response
        try:
            # Look for JSON-like structure in the response
            json_match = re.search(r'({[\s\S]*})', response)
            if json_match:
                json_str = json_match.group(1)
                financial_data = json.loads(json_str)
                logger.info("Successfully extracted JSON from LLM response")

                # Validate the structure of the financial data
                if not self._validate_financial_data(financial_data):
                    logger.warning("Financial data from LLM has invalid structure")
                    raise ValueError("Invalid financial data structure")

                # Update instance variables
                self.years = financial_data.get("years", [])
                self.balance_sheet_data = financial_data.get("balance_sheet", {})
                self.income_statement_data = financial_data.get("income_statement", {})
                self.cash_flow_data = financial_data.get("cash_flow", {})
                self.ratios = financial_data.get("ratios", {})

                return financial_data
            else:
                logger.warning("No JSON found in LLM response")
                raise ValueError("No JSON found in LLM response")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from LLM response: {str(e)}")
            raise

    def _validate_financial_data(self, financial_data: Dict[str, Any]) -> bool:
        """
        Validate the structure of the financial data.

        Args:
            financial_data: The financial data to validate

        Returns:
            True if the financial data is valid, False otherwise
        """
        # Check if the financial data has the required keys
        required_keys = ["years", "balance_sheet", "income_statement", "cash_flow"]
        for key in required_keys:
            if key not in financial_data:
                logger.warning(f"Financial data missing required key: {key}")
                return False

        # Check if the years key is a list
        if not isinstance(financial_data["years"], list):
            logger.warning("Financial data years is not a list")
            return False

        # Check if the balance_sheet, income_statement, and cash_flow keys are dictionaries
        for key in ["balance_sheet", "income_statement", "cash_flow"]:
            if not isinstance(financial_data[key], dict):
                logger.warning(f"Financial data {key} is not a dictionary")
                return False

        # All checks passed
        return True