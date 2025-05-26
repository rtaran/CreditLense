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

    def _create_improved_extraction_prompt(self) -> str:
        """
        Create an improved prompt for the LLM to extract financial data.

        Returns:
            A prompt for the LLM
        """
        prompt = """
        You are a financial data extraction expert. I will provide you with text from a financial statement PDF.
        Your task is to extract the following financial data:
        1. Years covered in the financial statements
        2. Balance sheet data for each year
        3. Income statement data for each year
        4. Cash flow data for each year
        5. Financial ratios (if available) or calculate them based on the data

        Format your response as a JSON object with the following structure:
        {
            "years": [list of years as integers],
            "balance_sheet": {
                "YEAR": {
                    "Current Assets": {
                        "Cash and Cash Equivalents": value,
                        "Accounts Receivable": value,
                        ...
                        "Total Current Assets": value
                    },
                    "Non-Current Assets": {
                        ...
                        "Total Non-Current Assets": value
                    },
                    "Current Liabilities": {
                        ...
                        "Total Current Liabilities": value
                    },
                    "Non-Current Liabilities": {
                        ...
                        "Total Non-Current Liabilities": value
                    },
                    "Equity": {
                        ...
                        "Total Equity": value
                    }
                }
            },
            "income_statement": {
                "YEAR": {
                    "Revenue": {
                        "Revenue": value,
                        "Total Revenue": value
                    },
                    "Expenses": {
                        "Cost of Goods Sold": value,
                        ...
                    },
                    "Profit": {
                        "Gross Profit": value,
                        "Operating Income": value,
                        "Net Income": value
                    }
                }
            },
            "cash_flow": {
                "YEAR": {
                    "Operating Activities": {
                        ...
                        "Net Cash from Operating Activities": value
                    },
                    "Investing Activities": {
                        ...
                        "Net Cash from Investing Activities": value
                    },
                    "Financing Activities": {
                        ...
                        "Net Cash from Financing Activities": value
                    }
                }
            },
            "ratios": {
                "YEAR": {
                    "Liquidity": {
                        "Current Ratio": value,
                        "Quick Ratio": value
                    },
                    "Solvency": {
                        "Debt-to-Equity Ratio": value,
                        "Debt-to-Assets Ratio": value
                    },
                    "Profitability": {
                        "Net Profit Margin": value,
                        "Return on Assets": value,
                        "Return on Equity": value
                    }
                }
            }
        }

        Here is the financial statement text:
        """
        prompt += self.pdf_text
        return prompt

    def _improved_parse_llm_response(self, response: str) -> Dict[str, Any]:
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

    def extract_all_data(self) -> Dict[str, Any]:
        """
        Extract all financial data using regex-based methods.

        Returns:
            A dictionary containing all extracted financial data
        """
        logger.info("Extracting all financial data using regex-based methods")

        # Extract the years
        self.years = self._extract_years()
        logger.info(f"Extracted years: {self.years}")

        # Extract the balance sheet data
        self.balance_sheet_data = self._extract_balance_sheet_data()

        # Extract the income statement data
        self.income_statement_data = self._extract_income_statement_data()

        # Extract the cash flow data
        self.cash_flow_data = self._extract_cash_flow_data()

        # Calculate the financial ratios
        self.ratios = self._calculate_financial_ratios()

        # Prepare the result
        result = {
            "years": self.years,
            "balance_sheet": self.balance_sheet_data,
            "income_statement": self.income_statement_data,
            "cash_flow": self.cash_flow_data,
            "ratios": self.ratios
        }

        return result

    def _extract_years(self) -> List[int]:
        """
        Extract years from the PDF text.

        Returns:
            A list of years
        """
        # Use regex to find years in the text
        year_pattern = r'\b(19|20)\d{2}\b'
        years = [int(year) for year in re.findall(year_pattern, self.pdf_text)]

        # Filter out future years
        current_year = datetime.now().year
        years = [year for year in years if year <= current_year]

        # Remove duplicates and sort
        years = sorted(list(set(years)))

        return years

    def _extract_balance_sheet_data(self) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Extract balance sheet data from the PDF text.

        Returns:
            A dictionary containing the balance sheet data for each year
        """
        # Initialize the result
        result = {}

        # Extract the balance sheet data for each year
        for year in self.years:
            result[year] = {
                "Current Assets": {},
                "Non-Current Assets": {},
                "Current Liabilities": {},
                "Non-Current Liabilities": {},
                "Equity": {}
            }

            # Get the context around the year mention
            context = self._get_year_context(year)
            if not context:
                continue

            # Extract Current Assets
            cash = self._extract_value_for_item("Cash and Cash Equivalents", year)
            if cash is not None:
                result[year]["Current Assets"]["Cash and Cash Equivalents"] = cash

            accounts_receivable = self._extract_value_for_item("Accounts Receivable", year)
            if accounts_receivable is not None:
                result[year]["Current Assets"]["Accounts Receivable"] = accounts_receivable

            inventory = self._extract_value_for_item("Inventory", year)
            if inventory is not None:
                result[year]["Current Assets"]["Inventory"] = inventory

            prepaid_expenses = self._extract_value_for_item("Prepaid Expenses", year)
            if prepaid_expenses is not None:
                result[year]["Current Assets"]["Prepaid Expenses"] = prepaid_expenses

            total_current_assets = self._extract_value_for_item("Total Current Assets", year)
            if total_current_assets is not None:
                result[year]["Current Assets"]["Total Current Assets"] = total_current_assets

            # Extract Non-Current Assets
            property_plant_equipment = self._extract_value_for_item("Property, Plant and Equipment", year)
            if property_plant_equipment is not None:
                result[year]["Non-Current Assets"]["Property, Plant and Equipment"] = property_plant_equipment

            intangible_assets = self._extract_value_for_item("Intangible Assets", year)
            if intangible_assets is not None:
                result[year]["Non-Current Assets"]["Intangible Assets"] = intangible_assets

            investments = self._extract_value_for_item("Investments", year)
            if investments is not None:
                result[year]["Non-Current Assets"]["Investments"] = investments

            total_non_current_assets = self._extract_value_for_item("Total Non-Current Assets", year)
            if total_non_current_assets is not None:
                result[year]["Non-Current Assets"]["Total Non-Current Assets"] = total_non_current_assets

            # Extract Current Liabilities
            accounts_payable = self._extract_value_for_item("Accounts Payable", year)
            if accounts_payable is not None:
                result[year]["Current Liabilities"]["Accounts Payable"] = accounts_payable

            short_term_debt = self._extract_value_for_item("Short-term Debt", year)
            if short_term_debt is not None:
                result[year]["Current Liabilities"]["Short-term Debt"] = short_term_debt

            accrued_expenses = self._extract_value_for_item("Accrued Expenses", year)
            if accrued_expenses is not None:
                result[year]["Current Liabilities"]["Accrued Expenses"] = accrued_expenses

            total_current_liabilities = self._extract_value_for_item("Total Current Liabilities", year)
            if total_current_liabilities is not None:
                result[year]["Current Liabilities"]["Total Current Liabilities"] = total_current_liabilities

            # Extract Non-Current Liabilities
            long_term_debt = self._extract_value_for_item("Long-term Debt", year)
            if long_term_debt is not None:
                result[year]["Non-Current Liabilities"]["Long-term Debt"] = long_term_debt

            deferred_tax_liabilities = self._extract_value_for_item("Deferred Tax Liabilities", year)
            if deferred_tax_liabilities is not None:
                result[year]["Non-Current Liabilities"]["Deferred Tax Liabilities"] = deferred_tax_liabilities

            total_non_current_liabilities = self._extract_value_for_item("Total Non-Current Liabilities", year)
            if total_non_current_liabilities is not None:
                result[year]["Non-Current Liabilities"]["Total Non-Current Liabilities"] = total_non_current_liabilities

            # Extract Equity
            common_stock = self._extract_value_for_item("Common Stock", year)
            if common_stock is not None:
                result[year]["Equity"]["Common Stock"] = common_stock

            retained_earnings = self._extract_value_for_item("Retained Earnings", year)
            if retained_earnings is not None:
                result[year]["Equity"]["Retained Earnings"] = retained_earnings

            total_equity = self._extract_value_for_item("Total Equity", year)
            if total_equity is not None:
                result[year]["Equity"]["Total Equity"] = total_equity

        return result

    def _extract_income_statement_data(self) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Extract income statement data from the PDF text.

        Returns:
            A dictionary containing the income statement data for each year
        """
        # Initialize the result
        result = {}

        # Extract the income statement data for each year
        for year in self.years:
            result[year] = {
                "Revenue": {},
                "Expenses": {},
                "Profit": {}
            }

            # Get the context around the year mention
            context = self._get_year_context(year)
            if not context:
                continue

            # Extract Revenue items
            revenue = self._extract_value_for_item("Revenue", year)
            if revenue is not None:
                result[year]["Revenue"]["Revenue"] = revenue

            sales = self._extract_value_for_item("Sales", year)
            if sales is not None:
                result[year]["Revenue"]["Sales"] = sales

            service_revenue = self._extract_value_for_item("Service Revenue", year)
            if service_revenue is not None:
                result[year]["Revenue"]["Service Revenue"] = service_revenue

            total_revenue = self._extract_value_for_item("Total Revenue", year)
            if total_revenue is not None:
                result[year]["Revenue"]["Total Revenue"] = total_revenue

            # Extract Expense items
            cost_of_goods_sold = self._extract_value_for_item("Cost of Goods Sold", year)
            if cost_of_goods_sold is not None:
                result[year]["Expenses"]["Cost of Goods Sold"] = cost_of_goods_sold

            operating_expenses = self._extract_value_for_item("Operating Expenses", year)
            if operating_expenses is not None:
                result[year]["Expenses"]["Operating Expenses"] = operating_expenses

            selling_general_admin = self._extract_value_for_item("Selling, General and Administrative", year)
            if selling_general_admin is not None:
                result[year]["Expenses"]["Selling, General and Administrative"] = selling_general_admin

            research_development = self._extract_value_for_item("Research and Development", year)
            if research_development is not None:
                result[year]["Expenses"]["Research and Development"] = research_development

            depreciation_amortization = self._extract_value_for_item("Depreciation and Amortization", year)
            if depreciation_amortization is not None:
                result[year]["Expenses"]["Depreciation and Amortization"] = depreciation_amortization

            interest_expense = self._extract_value_for_item("Interest Expense", year)
            if interest_expense is not None:
                result[year]["Expenses"]["Interest Expense"] = interest_expense

            income_tax_expense = self._extract_value_for_item("Income Tax Expense", year)
            if income_tax_expense is not None:
                result[year]["Expenses"]["Income Tax Expense"] = income_tax_expense

            total_expenses = self._extract_value_for_item("Total Expenses", year)
            if total_expenses is not None:
                result[year]["Expenses"]["Total Expenses"] = total_expenses

            # Extract Profit items
            gross_profit = self._extract_value_for_item("Gross Profit", year)
            if gross_profit is not None:
                result[year]["Profit"]["Gross Profit"] = gross_profit

            operating_income = self._extract_value_for_item("Operating Income", year)
            if operating_income is not None:
                result[year]["Profit"]["Operating Income"] = operating_income

            income_before_tax = self._extract_value_for_item("Income Before Tax", year)
            if income_before_tax is not None:
                result[year]["Profit"]["Income Before Tax"] = income_before_tax

            net_income = self._extract_value_for_item("Net Income", year)
            if net_income is not None:
                result[year]["Profit"]["Net Income"] = net_income

        return result

    def _extract_cash_flow_data(self) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Extract cash flow data from the PDF text.

        Returns:
            A dictionary containing the cash flow data for each year
        """
        # Initialize the result
        result = {}

        # Extract the cash flow data for each year
        for year in self.years:
            result[year] = {
                "Operating Activities": {},
                "Investing Activities": {},
                "Financing Activities": {}
            }

            # Get the context around the year mention
            context = self._get_year_context(year)
            if not context:
                continue

            # Extract Operating Activities items
            net_income = self._extract_value_for_item("Net Income", year)
            if net_income is not None:
                result[year]["Operating Activities"]["Net Income"] = net_income

            depreciation_amortization = self._extract_value_for_item("Depreciation and Amortization", year)
            if depreciation_amortization is not None:
                result[year]["Operating Activities"]["Depreciation and Amortization"] = depreciation_amortization

            changes_in_working_capital = self._extract_value_for_item("Changes in Working Capital", year)
            if changes_in_working_capital is not None:
                result[year]["Operating Activities"]["Changes in Working Capital"] = changes_in_working_capital

            net_cash_operating = self._extract_value_for_item("Net Cash from Operating Activities", year)
            if net_cash_operating is not None:
                result[year]["Operating Activities"]["Net Cash from Operating Activities"] = net_cash_operating

            # Extract Investing Activities items
            capital_expenditures = self._extract_value_for_item("Capital Expenditures", year)
            if capital_expenditures is not None:
                result[year]["Investing Activities"]["Capital Expenditures"] = capital_expenditures

            acquisitions = self._extract_value_for_item("Acquisitions", year)
            if acquisitions is not None:
                result[year]["Investing Activities"]["Acquisitions"] = acquisitions

            investments = self._extract_value_for_item("Investments", year)
            if investments is not None:
                result[year]["Investing Activities"]["Investments"] = investments

            net_cash_investing = self._extract_value_for_item("Net Cash from Investing Activities", year)
            if net_cash_investing is not None:
                result[year]["Investing Activities"]["Net Cash from Investing Activities"] = net_cash_investing

            # Extract Financing Activities items
            debt_issuance = self._extract_value_for_item("Debt Issuance", year)
            if debt_issuance is not None:
                result[year]["Financing Activities"]["Debt Issuance"] = debt_issuance

            debt_repayment = self._extract_value_for_item("Debt Repayment", year)
            if debt_repayment is not None:
                result[year]["Financing Activities"]["Debt Repayment"] = debt_repayment

            dividends_paid = self._extract_value_for_item("Dividends Paid", year)
            if dividends_paid is not None:
                result[year]["Financing Activities"]["Dividends Paid"] = dividends_paid

            stock_repurchase = self._extract_value_for_item("Stock Repurchase", year)
            if stock_repurchase is not None:
                result[year]["Financing Activities"]["Stock Repurchase"] = stock_repurchase

            net_cash_financing = self._extract_value_for_item("Net Cash from Financing Activities", year)
            if net_cash_financing is not None:
                result[year]["Financing Activities"]["Net Cash from Financing Activities"] = net_cash_financing

        return result

    def _calculate_financial_ratios(self) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Calculate financial ratios based on the extracted data.

        Returns:
            A dictionary containing the financial ratios for each year
        """
        # Initialize the result
        result = {}

        # Calculate the financial ratios for each year
        for year in self.years:
            result[year] = {
                "Liquidity": {},
                "Solvency": {},
                "Profitability": {}
            }

            # Get the balance sheet data for the year
            balance_sheet = self.balance_sheet_data.get(year, {})

            # Get the income statement data for the year
            income_statement = self.income_statement_data.get(year, {})

            # Get the cash flow data for the year
            cash_flow = self.cash_flow_data.get(year, {})

            # Calculate Liquidity Ratios

            # Current Ratio = Current Assets / Current Liabilities
            current_assets = self._get_nested_value(balance_sheet, ["Current Assets", "Total Current Assets"])
            current_liabilities = self._get_nested_value(balance_sheet, ["Current Liabilities", "Total Current Liabilities"])

            if current_assets is not None and current_liabilities is not None and current_liabilities != 0:
                result[year]["Liquidity"]["Current Ratio"] = current_assets / current_liabilities

            # Quick Ratio = (Current Assets - Inventory) / Current Liabilities
            inventory = self._get_nested_value(balance_sheet, ["Current Assets", "Inventory"])

            if current_assets is not None and inventory is not None and current_liabilities is not None and current_liabilities != 0:
                result[year]["Liquidity"]["Quick Ratio"] = (current_assets - inventory) / current_liabilities

            # Calculate Solvency Ratios

            # Debt-to-Equity Ratio = Total Liabilities / Total Equity
            total_liabilities = 0
            if current_liabilities is not None:
                total_liabilities += current_liabilities

            non_current_liabilities = self._get_nested_value(balance_sheet, ["Non-Current Liabilities", "Total Non-Current Liabilities"])
            if non_current_liabilities is not None:
                total_liabilities += non_current_liabilities

            total_equity = self._get_nested_value(balance_sheet, ["Equity", "Total Equity"])

            if total_liabilities > 0 and total_equity is not None and total_equity != 0:
                result[year]["Solvency"]["Debt-to-Equity Ratio"] = total_liabilities / total_equity

            # Debt-to-Assets Ratio = Total Liabilities / Total Assets
            total_assets = 0
            if current_assets is not None:
                total_assets += current_assets

            non_current_assets = self._get_nested_value(balance_sheet, ["Non-Current Assets", "Total Non-Current Assets"])
            if non_current_assets is not None:
                total_assets += non_current_assets

            if total_liabilities > 0 and total_assets > 0:
                result[year]["Solvency"]["Debt-to-Assets Ratio"] = total_liabilities / total_assets

            # Calculate Profitability Ratios

            # Net Profit Margin = Net Income / Total Revenue
            net_income = self._get_nested_value(income_statement, ["Profit", "Net Income"])
            total_revenue = self._get_nested_value(income_statement, ["Revenue", "Total Revenue"])

            if net_income is not None and total_revenue is not None and total_revenue != 0:
                result[year]["Profitability"]["Net Profit Margin"] = net_income / total_revenue

            # Return on Assets (ROA) = Net Income / Total Assets
            if net_income is not None and total_assets > 0:
                result[year]["Profitability"]["Return on Assets"] = net_income / total_assets

            # Return on Equity (ROE) = Net Income / Total Equity
            if net_income is not None and total_equity is not None and total_equity != 0:
                result[year]["Profitability"]["Return on Equity"] = net_income / total_equity

        return result

    def _extract_value_for_item(self, item: str, year: int) -> Optional[float]:
        """
        Extract a value for a specific item and year.

        Args:
            item: The item to extract the value for
            year: The year to extract the value for

        Returns:
            The extracted value, or None if it cannot be extracted
        """
        # Get the context around the year mention
        context = self._get_year_context(year)
        if not context:
            return None

        # Use regex to find the item and its value
        # This is a simplified implementation
        # In a real-world scenario, you would use more sophisticated regex patterns
        # or NLP techniques to extract the values

        # Example pattern: "Item Name 1000"
        pattern = rf'{re.escape(item)}\s+(\d+(?:\.\d+)?)'
        match = re.search(pattern, context)
        if match:
            return float(match.group(1))

        return None

    def _get_year_context(self, year: int) -> Optional[str]:
        """
        Get the context around a year mention in the PDF text.

        Args:
            year: The year to get the context for

        Returns:
            The context, or None if the year is not found
        """
        # Find the year in the text
        year_pattern = rf'\b{year}\b'
        match = re.search(year_pattern, self.pdf_text)
        if not match:
            return None

        # Get the context around the year mention
        # This is a simplified implementation
        # In a real-world scenario, you would use more sophisticated techniques
        # to extract the relevant context

        # Get 500 characters before and after the year mention
        start = max(0, match.start() - 500)
        end = min(len(self.pdf_text), match.end() + 500)
        context = self.pdf_text[start:end]

        return context

    def _get_nested_value(self, data: Dict[str, Any], keys: List[str]) -> Optional[float]:
        """
        Get a nested value from a dictionary.

        Args:
            data: The dictionary to get the value from
            keys: The keys to traverse to get the value

        Returns:
            The value, or None if it cannot be found
        """
        try:
            current = data
            for key in keys:
                if key in current:
                    current = current[key]
                else:
                    return None
            return current if isinstance(current, (int, float)) else None
        except Exception:
            return None

    def _calculate_ratio(self, ratio_name: str, year: int) -> Optional[float]:
        """
        Calculate a financial ratio for a specific year.

        Args:
            ratio_name: The name of the ratio to calculate
            year: The year to calculate the ratio for

        Returns:
            The calculated ratio, or None if it cannot be calculated
        """
        try:
            # Get the balance sheet data for the year
            balance_sheet = self.balance_sheet_data.get(year, {})

            # Get the income statement data for the year
            income_statement = self.income_statement_data.get(year, {})

            # Calculate the ratio based on its name
            if ratio_name == "Current Ratio":
                current_assets = self._get_value_from_dict(balance_sheet, ["Current Assets", "Total Current Assets"])
                current_liabilities = self._get_value_from_dict(balance_sheet, ["Current Liabilities", "Total Current Liabilities"])
                if current_assets is not None and current_liabilities is not None and current_liabilities != 0:
                    return current_assets / current_liabilities

            elif ratio_name == "Quick Ratio":
                current_assets = self._get_value_from_dict(balance_sheet, ["Current Assets", "Total Current Assets"])
                inventory = self._get_value_from_dict(balance_sheet, ["Current Assets", "Inventory"])
                current_liabilities = self._get_value_from_dict(balance_sheet, ["Current Liabilities", "Total Current Liabilities"])
                if current_assets is not None and inventory is not None and current_liabilities is not None and current_liabilities != 0:
                    return (current_assets - inventory) / current_liabilities

            elif ratio_name == "Debt-to-Equity Ratio":
                total_liabilities = self._get_value_from_dict(balance_sheet, ["Current Liabilities", "Total Current Liabilities"])
                total_liabilities += self._get_value_from_dict(balance_sheet, ["Non-Current Liabilities", "Total Non-Current Liabilities"]) or 0
                total_equity = self._get_value_from_dict(balance_sheet, ["Equity", "Total Equity"])
                if total_liabilities is not None and total_equity is not None and total_equity != 0:
                    return total_liabilities / total_equity

            elif ratio_name == "Net Profit Margin":
                net_income = self._get_value_from_dict(income_statement, ["Profit", "Net Income"])
                total_revenue = self._get_value_from_dict(income_statement, ["Revenue", "Total Revenue"])
                if net_income is not None and total_revenue is not None and total_revenue != 0:
                    return (net_income / total_revenue) * 100

            # Add more ratios as needed

            return None
        except Exception as e:
            logger.error(f"Error calculating ratio {ratio_name} for year {year}: {str(e)}")
            return None

    def _get_value_from_dict(self, data_dict: Dict, keys: List) -> Optional[float]:
        """
        Safely get a value from a nested dictionary.

        Args:
            data_dict: The dictionary to get the value from
            keys: A list of keys to navigate the dictionary

        Returns:
            The value, or None if the key path doesn't exist
        """
        try:
            current = data_dict
            for key in keys:
                if key in current:
                    current = current[key]
                else:
                    return None
            return current if isinstance(current, (int, float)) else None
        except Exception:
            return None


def store_financial_data(db: Session, document_id: int, financial_data: Dict[str, Any]) -> None:
    """
    Store financial data in the database.

    Args:
        db: The database session
        document_id: The ID of the document
        financial_data: The financial data to store
    """
    logger.info(f"Storing financial data for document {document_id}")

    # Get the document
    document = db.query(CompanyData).filter(CompanyData.document_id == document_id).first()
    if not document:
        logger.error(f"Document {document_id} not found")
        return

    # Extract the years
    years = financial_data.get("years", [])
    if not years:
        logger.warning(f"No years found in financial data for document {document_id}")
        return

    # Store the financial data for each year
    for year in years:
        # Create a financial year
        financial_year = FinancialYear(
            document_id=document_id,
            year=year
        )
        db.add(financial_year)
        db.flush()  # Flush to get the year_id

        # Store balance sheet data
        balance_sheet = financial_data.get("balance_sheet", {}).get(str(year), {})
        for category, items in balance_sheet.items():
            for item_name, item_value in items.items():
                balance_sheet_item = BalanceSheetItem(
                    year_id=financial_year.year_id,
                    item_name=item_name,
                    item_value=item_value,
                    item_category=category
                )
                db.add(balance_sheet_item)

        # Store income statement data
        income_statement = financial_data.get("income_statement", {}).get(str(year), {})
        for category, items in income_statement.items():
            for item_name, item_value in items.items():
                income_statement_item = IncomeStatementItem(
                    year_id=financial_year.year_id,
                    item_name=item_name,
                    item_value=item_value,
                    item_category=category
                )
                db.add(income_statement_item)

        # Store cash flow data
        cash_flow = financial_data.get("cash_flow", {}).get(str(year), {})
        for category, items in cash_flow.items():
            for item_name, item_value in items.items():
                cash_flow_item = CashFlowItem(
                    year_id=financial_year.year_id,
                    item_name=item_name,
                    item_value=item_value,
                    item_category=category
                )
                db.add(cash_flow_item)

        # Store financial ratios
        ratios = financial_data.get("ratios", {}).get(str(year), {})
        for category, items in ratios.items():
            for ratio_name, ratio_value in items.items():
                financial_ratio = FinancialRatio(
                    year_id=financial_year.year_id,
                    ratio_name=ratio_name,
                    ratio_value=ratio_value,
                    ratio_category=category
                )
                db.add(financial_ratio)

    # Commit the changes
    db.commit()
    logger.info(f"Financial data stored successfully for document {document_id}")


def get_financial_data_for_document(db: Session, document_id: int) -> Dict[str, Any]:
    """
    Get financial data for a document.

    Args:
        db: The database session
        document_id: The ID of the document

    Returns:
        A dictionary containing the financial data
    """
    logger.info(f"Getting financial data for document {document_id}")

    # Get the document
    document = db.query(CompanyData).filter(CompanyData.document_id == document_id).first()
    if not document:
        logger.error(f"Document {document_id} not found")
        return {}

    # Get the financial years
    financial_years = db.query(FinancialYear).filter(FinancialYear.document_id == document_id).all()
    if not financial_years:
        logger.warning(f"No financial years found for document {document_id}")
        return {}

    # Initialize the result
    result = {
        "years": [],
        "balance_sheet": {},
        "income_statement": {},
        "cash_flow": {},
        "ratios": {}
    }

    # Extract the years
    result["years"] = [year.year for year in financial_years]

    # Extract the financial data for each year
    for year in financial_years:
        # Extract balance sheet data
        balance_sheet_items = db.query(BalanceSheetItem).filter(BalanceSheetItem.year_id == year.year_id).all()
        if balance_sheet_items:
            result["balance_sheet"][year.year] = {}
            for item in balance_sheet_items:
                if item.item_category not in result["balance_sheet"][year.year]:
                    result["balance_sheet"][year.year][item.item_category] = {}
                result["balance_sheet"][year.year][item.item_category][item.item_name] = item.item_value

        # Extract income statement data
        income_statement_items = db.query(IncomeStatementItem).filter(IncomeStatementItem.year_id == year.year_id).all()
        if income_statement_items:
            result["income_statement"][year.year] = {}
            for item in income_statement_items:
                if item.item_category not in result["income_statement"][year.year]:
                    result["income_statement"][year.year][item.item_category] = {}
                result["income_statement"][year.year][item.item_category][item.item_name] = item.item_value

        # Extract cash flow data
        cash_flow_items = db.query(CashFlowItem).filter(CashFlowItem.year_id == year.year_id).all()
        if cash_flow_items:
            result["cash_flow"][year.year] = {}
            for item in cash_flow_items:
                if item.item_category not in result["cash_flow"][year.year]:
                    result["cash_flow"][year.year][item.item_category] = {}
                result["cash_flow"][year.year][item.item_category][item.item_name] = item.item_value

        # Extract financial ratios
        financial_ratios = db.query(FinancialRatio).filter(FinancialRatio.year_id == year.year_id).all()
        if financial_ratios:
            result["ratios"][year.year] = {}
            for ratio in financial_ratios:
                if ratio.ratio_category not in result["ratios"][year.year]:
                    result["ratios"][year.year][ratio.ratio_category] = {}
                result["ratios"][year.year][ratio.ratio_category][ratio.ratio_name] = ratio.ratio_value

    logger.info(f"Financial data retrieved successfully for document {document_id}")
    return result
