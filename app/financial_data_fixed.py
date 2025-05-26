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
        Initialize with the PDF text to extract data from.

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