"""
Module for extracting and processing financial data from PDFs.
"""
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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialDataExtractor:
    """
    Class for extracting financial data from PDF text.
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

        # Truncate the PDF text to avoid exceeding token limits
        max_doc_length = 12000
        original_length = len(self.pdf_text)
        truncated_text = self.pdf_text[:max_doc_length]

        if original_length > max_doc_length:
            logger.info(f"PDF text truncated from {original_length} to {max_doc_length} characters")
        else:
            logger.debug(f"PDF text length ({original_length} characters) is within limits")

        # Create a prompt for the LLM
        logger.info("Creating extraction prompt for LLM")
        prompt = self._create_extraction_prompt(truncated_text)

        # Generate the financial data using the LLM service
        logger.info(f"Sending prompt to LLM using {provider or 'default'} provider")
        try:
            response = llm_service.generate_text(prompt, provider=provider)
            logger.info(f"Received response from LLM with length {len(response)} characters")
        except Exception as e:
            logger.error(f"Error generating financial data with LLM: {str(e)}")
            # Fall back to regex-based extraction if LLM fails
            logger.info("Falling back to regex-based extraction")
            return self.extract_all_data()

        # Parse the LLM's response to extract the financial data
        logger.info("Parsing LLM response to extract financial data")
        try:
            financial_data = self._parse_llm_response(response)
            logger.info(f"Successfully parsed financial data from LLM response")
            return financial_data
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            # Fall back to regex-based extraction if parsing fails
            logger.info("Falling back to regex-based extraction")
            return self.extract_all_data()

    def _create_extraction_prompt(self, pdf_text: str) -> str:
        """
        Create a prompt for the LLM to extract financial data.

        Args:
            pdf_text: The text content of the PDF

        Returns:
            A prompt for the LLM
        """
        prompt = f"""
        You are a financial data extraction expert. Extract the following financial data from the provided financial document:

        1. Reporting years (list all years found in the document)
        2. Balance sheet data for each year, including:
           - Current Assets (Cash and Cash Equivalents, Short-term Investments, Accounts Receivable, Inventory, Prepaid Expenses, Total Current Assets)
           - Non-Current Assets (Property, Plant and Equipment, Intangible Assets, Goodwill, Long-term Investments, Deferred Tax Assets, Total Non-Current Assets)
           - Current Liabilities (Accounts Payable, Short-term Debt, Current Portion of Long-term Debt, Accrued Expenses, Deferred Revenue, Total Current Liabilities)
           - Non-Current Liabilities (Long-term Debt, Pension Liabilities, Deferred Tax Liabilities, Total Non-Current Liabilities)
           - Equity (Common Stock, Retained Earnings, Additional Paid-in Capital, Treasury Stock, Total Equity)
        3. Income statement data for each year, including:
           - Revenue (Revenue, Net Sales, Total Revenue)
           - Expenses (Cost of Goods Sold, Gross Profit, Operating Expenses, Research and Development, Selling, General and Administrative, Depreciation and Amortization)
           - Profit (Operating Income, Interest Expense, Income Before Tax, Income Tax Expense, Net Income)
           - Per Share Data (Basic Earnings Per Share, Diluted Earnings Per Share, Dividends Per Share)
        4. Cash flow data for each year, including:
           - Operating Activities (Net Income, Depreciation and Amortization, Changes in Working Capital, Net Cash from Operating Activities)
           - Investing Activities (Capital Expenditures, Acquisitions, Purchases of Investments, Sales of Investments, Net Cash from Investing Activities)
           - Financing Activities (Debt Issuance, Debt Repayment, Dividends Paid, Share Repurchases, Net Cash from Financing Activities)
           - Summary (Net Change in Cash, Cash at Beginning of Period, Cash at End of Period)
        5. Financial ratios for each year, including:
           - Liquidity (Current Ratio, Quick Ratio, Cash Ratio)
           - Solvency (Debt-to-Equity Ratio, Debt-to-Assets Ratio, Interest Coverage Ratio)
           - Profitability (Gross Margin, Operating Margin, Net Profit Margin, Return on Assets, Return on Equity)
           - Efficiency (Asset Turnover, Inventory Turnover, Receivables Turnover)

        Format your response as a JSON object with the following structure:
        {{
            "years": [list of years as integers],
            "balance_sheet": {{
                "year1": {{
                    "category1": {{
                        "item1": value1,
                        "item2": value2,
                        ...
                    }},
                    ...
                }},
                ...
            }},
            "income_statement": {{
                "year1": {{
                    "category1": {{
                        "item1": value1,
                        "item2": value2,
                        ...
                    }},
                    ...
                }},
                ...
            }},
            "cash_flow": {{
                "year1": {{
                    "category1": {{
                        "item1": value1,
                        "item2": value2,
                        ...
                    }},
                    ...
                }},
                ...
            }},
            "ratios": {{
                "year1": {{
                    "category1": {{
                        "ratio1": value1,
                        "ratio2": value2,
                        ...
                    }},
                    ...
                }},
                ...
            }}
        }}

        If you cannot find a specific value, use null instead. Only include the data you can find in the document.

        DOCUMENT:
        {pdf_text}
        """
        return prompt

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
            True if the financial data has a valid structure, False otherwise
        """
        # Check if the financial data has the required keys
        required_keys = ["years", "balance_sheet", "income_statement", "cash_flow", "ratios"]
        for key in required_keys:
            if key not in financial_data:
                logger.warning(f"Financial data missing required key: {key}")
                return False

        # Check if years is a list
        if not isinstance(financial_data["years"], list):
            logger.warning("Years is not a list")
            return False

        # Check if the other keys are dictionaries
        for key in required_keys[1:]:
            if not isinstance(financial_data[key], dict):
                logger.warning(f"{key} is not a dictionary")
                return False

        return True

    def extract_all_data(self) -> Dict[str, Any]:
        """
        Extract all financial data from the PDF text.

        Returns:
            A dictionary containing all extracted financial data
        """
        logger.info("Starting extraction of all financial data")

        logger.info("Extracting years from financial document")
        self._extract_years()
        logger.info(f"Extracted {len(self.years)} years: {self.years}")

        logger.info("Extracting balance sheet data")
        self._extract_balance_sheet_data()
        logger.info(f"Balance sheet data extracted for {len(self.balance_sheet_data)} years")

        logger.info("Extracting income statement data")
        self._extract_income_statement_data()
        logger.info(f"Income statement data extracted for {len(self.income_statement_data)} years")

        logger.info("Extracting cash flow data")
        self._extract_cash_flow_data()
        logger.info(f"Cash flow data extracted for {len(self.cash_flow_data)} years")

        logger.info("Calculating financial ratios")
        self._calculate_financial_ratios()
        logger.info(f"Financial ratios calculated for {len(self.ratios)} years")

        logger.info("Financial data extraction completed successfully")
        return {
            "years": self.years,
            "balance_sheet": self.balance_sheet_data,
            "income_statement": self.income_statement_data,
            "cash_flow": self.cash_flow_data,
            "ratios": self.ratios
        }

    def _extract_years(self) -> List[int]:
        """
        Extract the reporting years from the PDF text.

        Returns:
            A list of years found in the document
        """
        # Look for years in the format YYYY or 'Year ended December 31, YYYY'
        year_pattern = r'\b(20\d{2})\b'
        years = re.findall(year_pattern, self.pdf_text)

        # Convert to integers and remove duplicates
        unique_years = sorted(list(set([int(year) for year in years])))

        # Get current year
        from datetime import datetime
        current_year = datetime.now().year

        # Filter out future years
        valid_years = [year for year in unique_years if year <= current_year]

        if not valid_years:
            logger.warning("No valid years found in document. Using all extracted years.")
            valid_years = unique_years

        # Keep only the most recent years (typically financial statements show 2-3 years)
        self.years = valid_years[-3:] if len(valid_years) > 3 else valid_years

        logger.info(f"Extracted years: {self.years} (current year: {current_year})")

        return self.years

    def _extract_balance_sheet_data(self) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Extract balance sheet data from the PDF text.

        Returns:
            A dictionary mapping years to balance sheet items
        """
        # Common balance sheet items to look for
        balance_sheet_items = {
            "Current Assets": [
                "Cash and Cash Equivalents",
                "Short-term Investments",
                "Accounts Receivable",
                "Inventory",
                "Prepaid Expenses",
                "Total Current Assets"
            ],
            "Non-Current Assets": [
                "Property, Plant and Equipment",
                "Intangible Assets",
                "Goodwill",
                "Long-term Investments",
                "Deferred Tax Assets",
                "Total Non-Current Assets"
            ],
            "Current Liabilities": [
                "Accounts Payable",
                "Short-term Debt",
                "Current Portion of Long-term Debt",
                "Accrued Expenses",
                "Deferred Revenue",
                "Total Current Liabilities"
            ],
            "Non-Current Liabilities": [
                "Long-term Debt",
                "Pension Liabilities",
                "Deferred Tax Liabilities",
                "Total Non-Current Liabilities"
            ],
            "Equity": [
                "Common Stock",
                "Retained Earnings",
                "Additional Paid-in Capital",
                "Treasury Stock",
                "Total Equity"
            ]
        }

        # Initialize the balance sheet data dictionary
        for year in self.years:
            self.balance_sheet_data[year] = {}
            for category, items in balance_sheet_items.items():
                self.balance_sheet_data[year][category] = {}
                for item in items:
                    self.balance_sheet_data[year][category][item] = self._extract_value_for_item(item, year)

        return self.balance_sheet_data

    def _extract_income_statement_data(self) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Extract income statement data from the PDF text.

        Returns:
            A dictionary mapping years to income statement items
        """
        # Common income statement items to look for
        income_statement_items = {
            "Revenue": [
                "Revenue",
                "Net Sales",
                "Total Revenue"
            ],
            "Expenses": [
                "Cost of Goods Sold",
                "Gross Profit",
                "Operating Expenses",
                "Research and Development",
                "Selling, General and Administrative",
                "Depreciation and Amortization"
            ],
            "Profit": [
                "Operating Income",
                "Interest Expense",
                "Income Before Tax",
                "Income Tax Expense",
                "Net Income"
            ],
            "Per Share Data": [
                "Basic Earnings Per Share",
                "Diluted Earnings Per Share",
                "Dividends Per Share"
            ]
        }

        # Initialize the income statement data dictionary
        for year in self.years:
            self.income_statement_data[year] = {}
            for category, items in income_statement_items.items():
                self.income_statement_data[year][category] = {}
                for item in items:
                    self.income_statement_data[year][category][item] = self._extract_value_for_item(item, year)

        return self.income_statement_data

    def _extract_cash_flow_data(self) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Extract cash flow data from the PDF text.

        Returns:
            A dictionary mapping years to cash flow items
        """
        # Common cash flow items to look for
        cash_flow_items = {
            "Operating Activities": [
                "Net Income",
                "Depreciation and Amortization",
                "Changes in Working Capital",
                "Net Cash from Operating Activities"
            ],
            "Investing Activities": [
                "Capital Expenditures",
                "Acquisitions",
                "Purchases of Investments",
                "Sales of Investments",
                "Net Cash from Investing Activities"
            ],
            "Financing Activities": [
                "Debt Issuance",
                "Debt Repayment",
                "Dividends Paid",
                "Share Repurchases",
                "Net Cash from Financing Activities"
            ],
            "Summary": [
                "Net Change in Cash",
                "Cash at Beginning of Period",
                "Cash at End of Period"
            ]
        }

        # Initialize the cash flow data dictionary
        for year in self.years:
            self.cash_flow_data[year] = {}
            for category, items in cash_flow_items.items():
                self.cash_flow_data[year][category] = {}
                for item in items:
                    self.cash_flow_data[year][category][item] = self._extract_value_for_item(item, year)

        return self.cash_flow_data

    def _calculate_financial_ratios(self) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Calculate financial ratios based on the extracted data.

        Returns:
            A dictionary mapping years to financial ratios
        """
        # Define ratio categories and formulas
        ratio_categories = {
            "Liquidity": [
                "Current Ratio",
                "Quick Ratio",
                "Cash Ratio"
            ],
            "Solvency": [
                "Debt-to-Equity Ratio",
                "Debt-to-Assets Ratio",
                "Interest Coverage Ratio"
            ],
            "Profitability": [
                "Gross Margin",
                "Operating Margin",
                "Net Profit Margin",
                "Return on Assets (ROA)",
                "Return on Equity (ROE)"
            ],
            "Efficiency": [
                "Asset Turnover",
                "Inventory Turnover",
                "Receivables Turnover"
            ]
        }

        # Initialize the ratios dictionary
        for year in self.years:
            self.ratios[year] = {}
            for category, items in ratio_categories.items():
                self.ratios[year][category] = {}
                for item in items:
                    self.ratios[year][category][item] = self._calculate_ratio(item, year)

        return self.ratios

    def _extract_value_for_item(self, item: str, year: int) -> Optional[float]:
        """
        Extract a numerical value for a specific item and year from the PDF text.

        Args:
            item: The name of the financial item
            year: The year to extract the value for

        Returns:
            The extracted value as a float, or None if not found
        """
        # This is a simplified implementation
        # In a real-world scenario, this would use more sophisticated pattern matching
        # or NLP techniques to extract values accurately

        # Look for patterns like "Item Name ... $X,XXX" near the year
        year_str = str(year)
        item_pattern = fr'{re.escape(item)}[^\n]*?(\d+(?:,\d+)*(?:\.\d+)?)'

        # Search for the item in the context of the year
        year_context = self._get_year_context(year)
        if year_context:
            matches = re.findall(item_pattern, year_context)
            if matches:
                # Clean up and convert to float
                value_str = matches[0].replace(',', '')
                try:
                    return float(value_str)
                except ValueError:
                    return None

        return None

    def _get_year_context(self, year: int) -> Optional[str]:
        """
        Get the text context around a specific year mention.

        Args:
            year: The year to find context for

        Returns:
            A substring of the PDF text around the year mention, or None if not found
        """
        year_str = str(year)
        year_index = self.pdf_text.find(year_str)

        if year_index == -1:
            return None

        # Get a chunk of text around the year mention
        start_index = max(0, year_index - 5000)
        end_index = min(len(self.pdf_text), year_index + 5000)

        return self.pdf_text[start_index:end_index]

    def _calculate_ratio(self, ratio_name: str, year: int) -> Optional[float]:
        """
        Calculate a financial ratio for a specific year.

        Args:
            ratio_name: The name of the ratio to calculate
            year: The year to calculate the ratio for

        Returns:
            The calculated ratio as a float, or None if it cannot be calculated
        """
        # This is a simplified implementation
        # In a real-world scenario, this would use the actual financial data
        # to calculate ratios accurately

        if ratio_name == "Current Ratio":
            current_assets = self._get_value_from_dict(self.balance_sheet_data, [year, "Current Assets", "Total Current Assets"])
            current_liabilities = self._get_value_from_dict(self.balance_sheet_data, [year, "Current Liabilities", "Total Current Liabilities"])

            if current_assets is not None and current_liabilities is not None and current_liabilities != 0:
                return current_assets / current_liabilities

        elif ratio_name == "Debt-to-Equity Ratio":
            current_liabilities = self._get_value_from_dict(self.balance_sheet_data, [year, "Current Liabilities", "Total Current Liabilities"]) or 0
            non_current_liabilities = self._get_value_from_dict(self.balance_sheet_data, [year, "Non-Current Liabilities", "Total Non-Current Liabilities"]) or 0
            total_liabilities = current_liabilities + non_current_liabilities
            total_equity = self._get_value_from_dict(self.balance_sheet_data, [year, "Equity", "Total Equity"])

            if total_liabilities is not None and total_equity is not None and total_equity != 0:
                return total_liabilities / total_equity

        elif ratio_name == "Net Profit Margin":
            net_income = self._get_value_from_dict(self.income_statement_data, [year, "Profit", "Net Income"])
            revenue = self._get_value_from_dict(self.income_statement_data, [year, "Revenue", "Total Revenue"])

            if net_income is not None and revenue is not None and revenue != 0:
                return (net_income / revenue) * 100  # As percentage

        # Add more ratio calculations as needed

        return None

    def _get_value_from_dict(self, data_dict: Dict, keys: List) -> Optional[float]:
        """
        Safely get a value from a nested dictionary.

        Args:
            data_dict: The dictionary to get the value from
            keys: A list of keys to navigate the nested dictionary

        Returns:
            The value if found, or None if any key is missing
        """
        current = data_dict
        for key in keys:
            if key not in current:
                return None
            current = current[key]

        return current

def store_financial_data(db: Session, document_id: int, financial_data: Dict[str, Any]) -> None:
    """
    Store extracted financial data in the database.

    Args:
        db: The database session
        document_id: The ID of the document to associate the data with
        financial_data: The extracted financial data
    """
    logger.info(f"Starting to store financial data for document ID {document_id}")

    # Get the years from the financial data
    years = financial_data.get("years", [])
    logger.info(f"Found {len(years)} years of financial data to store: {years}")

    balance_sheet_count = 0
    income_statement_count = 0
    cash_flow_count = 0
    ratio_count = 0

    # Store data for each year
    for year in years:
        logger.info(f"Processing financial data for year {year}")

        # Create a FinancialYear record
        financial_year = FinancialYear(
            document_id=document_id,
            year=year
        )
        db.add(financial_year)
        db.flush()  # Flush to get the year_id
        logger.info(f"Created FinancialYear record with ID {financial_year.year_id} for year {year}")

        # Store balance sheet items
        logger.info(f"Storing balance sheet items for year {year}")
        balance_sheet_data = financial_data.get("balance_sheet", {}).get(year, {})
        year_balance_sheet_count = 0
        for category, items in balance_sheet_data.items():
            for item_name, item_value in items.items():
                if item_value is not None:
                    balance_sheet_item = BalanceSheetItem(
                        year_id=financial_year.year_id,
                        item_name=item_name,
                        item_value=item_value,
                        item_category=category
                    )
                    db.add(balance_sheet_item)
                    year_balance_sheet_count += 1
        logger.info(f"Stored {year_balance_sheet_count} balance sheet items for year {year}")
        balance_sheet_count += year_balance_sheet_count

        # Store income statement items
        logger.info(f"Storing income statement items for year {year}")
        income_statement_data = financial_data.get("income_statement", {}).get(year, {})
        year_income_statement_count = 0
        for category, items in income_statement_data.items():
            for item_name, item_value in items.items():
                if item_value is not None:
                    income_statement_item = IncomeStatementItem(
                        year_id=financial_year.year_id,
                        item_name=item_name,
                        item_value=item_value,
                        item_category=category
                    )
                    db.add(income_statement_item)
                    year_income_statement_count += 1
        logger.info(f"Stored {year_income_statement_count} income statement items for year {year}")
        income_statement_count += year_income_statement_count

        # Store cash flow items
        logger.info(f"Storing cash flow items for year {year}")
        cash_flow_data = financial_data.get("cash_flow", {}).get(year, {})
        year_cash_flow_count = 0
        for category, items in cash_flow_data.items():
            for item_name, item_value in items.items():
                if item_value is not None:
                    cash_flow_item = CashFlowItem(
                        year_id=financial_year.year_id,
                        item_name=item_name,
                        item_value=item_value,
                        item_category=category
                    )
                    db.add(cash_flow_item)
                    year_cash_flow_count += 1
        logger.info(f"Stored {year_cash_flow_count} cash flow items for year {year}")
        cash_flow_count += year_cash_flow_count

        # Store financial ratios
        logger.info(f"Storing financial ratios for year {year}")
        ratios_data = financial_data.get("ratios", {}).get(year, {})
        year_ratio_count = 0
        for category, items in ratios_data.items():
            for ratio_name, ratio_value in items.items():
                if ratio_value is not None:
                    financial_ratio = FinancialRatio(
                        year_id=financial_year.year_id,
                        ratio_name=ratio_name,
                        ratio_value=ratio_value,
                        ratio_category=category
                    )
                    db.add(financial_ratio)
                    year_ratio_count += 1
        logger.info(f"Stored {year_ratio_count} financial ratios for year {year}")
        ratio_count += year_ratio_count

    # Commit all changes
    logger.info("Committing all financial data to database")
    db.commit()
    logger.info(f"Successfully stored financial data for document ID {document_id}: {len(years)} years, {balance_sheet_count} balance sheet items, {income_statement_count} income statement items, {cash_flow_count} cash flow items, {ratio_count} financial ratios")

def get_financial_data_for_document(db: Session, document_id: int) -> Dict[str, Any]:
    """
    Retrieve all financial data for a document.

    Args:
        db: The database session
        document_id: The ID of the document to get data for

    Returns:
        A dictionary containing all financial data for the document
    """
    logger.info(f"Retrieving financial data for document ID {document_id}")

    # Get all financial years for the document
    financial_years = db.query(FinancialYear).filter(FinancialYear.document_id == document_id).all()
    logger.info(f"Found {len(financial_years)} financial years for document ID {document_id}")

    result = {
        "years": [],
        "balance_sheet": {},
        "income_statement": {},
        "cash_flow": {},
        "ratios": {}
    }

    balance_sheet_count = 0
    income_statement_count = 0
    cash_flow_count = 0
    ratio_count = 0

    for financial_year in financial_years:
        year = financial_year.year
        result["years"].append(year)
        logger.info(f"Processing financial data for year {year}")

        # Get balance sheet items
        logger.info(f"Retrieving balance sheet items for year {year}")
        balance_sheet_items = db.query(BalanceSheetItem).filter(BalanceSheetItem.year_id == financial_year.year_id).all()
        result["balance_sheet"][year] = {}
        for item in balance_sheet_items:
            if item.item_category not in result["balance_sheet"][year]:
                result["balance_sheet"][year][item.item_category] = {}
            result["balance_sheet"][year][item.item_category][item.item_name] = item.item_value
        logger.info(f"Retrieved {len(balance_sheet_items)} balance sheet items for year {year}")
        balance_sheet_count += len(balance_sheet_items)

        # Get income statement items
        logger.info(f"Retrieving income statement items for year {year}")
        income_statement_items = db.query(IncomeStatementItem).filter(IncomeStatementItem.year_id == financial_year.year_id).all()
        result["income_statement"][year] = {}
        for item in income_statement_items:
            if item.item_category not in result["income_statement"][year]:
                result["income_statement"][year][item.item_category] = {}
            result["income_statement"][year][item.item_category][item.item_name] = item.item_value
        logger.info(f"Retrieved {len(income_statement_items)} income statement items for year {year}")
        income_statement_count += len(income_statement_items)

        # Get cash flow items
        logger.info(f"Retrieving cash flow items for year {year}")
        cash_flow_items = db.query(CashFlowItem).filter(CashFlowItem.year_id == financial_year.year_id).all()
        result["cash_flow"][year] = {}
        for item in cash_flow_items:
            if item.item_category not in result["cash_flow"][year]:
                result["cash_flow"][year][item.item_category] = {}
            result["cash_flow"][year][item.item_category][item.item_name] = item.item_value
        logger.info(f"Retrieved {len(cash_flow_items)} cash flow items for year {year}")
        cash_flow_count += len(cash_flow_items)

        # Get financial ratios
        logger.info(f"Retrieving financial ratios for year {year}")
        financial_ratios = db.query(FinancialRatio).filter(FinancialRatio.year_id == financial_year.year_id).all()
        result["ratios"][year] = {}
        for ratio in financial_ratios:
            if ratio.ratio_category not in result["ratios"][year]:
                result["ratios"][year][ratio.ratio_category] = {}
            result["ratios"][year][ratio.ratio_category][ratio.ratio_name] = ratio.ratio_value
        logger.info(f"Retrieved {len(financial_ratios)} financial ratios for year {year}")
        ratio_count += len(financial_ratios)

    logger.info(f"Successfully retrieved financial data for document ID {document_id}: {len(financial_years)} years, {balance_sheet_count} balance sheet items, {income_statement_count} income statement items, {cash_flow_count} cash flow items, {ratio_count} financial ratios")
    return result
