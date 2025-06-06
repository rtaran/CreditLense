from app.llm_service import llm_service
from app.financial_data import get_financial_data_for_document
from sqlalchemy.orm import Session
import json
from typing import Dict, Any, Optional

class FinancialAnalyzer:
    """
    Analyzes financial documents and generates credit memos using LLM.
    """

    def __init__(self):
        """Initialize the financial analyzer."""
        pass

    def analyze_financial_document(self, document_text: str, provider: str = None, document_id: Optional[int] = None, db: Optional[Session] = None) -> str:
        """
        Analyze a financial document and generate a credit memo.

        Args:
            document_text: The text content of the financial document
            provider: The LLM provider to use (optional)
            document_id: The ID of the document in the database (optional)
            db: The database session (optional)

        Returns:
            A credit memo as text
        """
        # Get extracted financial data if document_id and db are provided
        financial_data = None
        if document_id is not None and db is not None:
            financial_data = get_financial_data_for_document(db, document_id)

        # Create a prompt for the LLM
        prompt = self._create_analysis_prompt(document_text, financial_data)

        # Generate the credit memo using the LLM service with the specified provider
        memo = llm_service.generate_text(prompt, provider=provider)

        return memo

    def _create_analysis_prompt(self, document_text: str, financial_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a prompt for the LLM to analyze a financial document.

        Args:
            document_text: The text content of the financial document
            financial_data: Extracted financial data (optional)

        Returns:
            A prompt for the LLM
        """
        # Limit the document text to avoid exceeding token limits
        max_doc_length = 8000  # Reduced to make room for financial data
        truncated_text = document_text[:max_doc_length]

        # Base prompt
        prompt = f"""
        You are a professional financial analyst tasked with creating a credit memo based on the following financial document.

        DOCUMENT:
        {truncated_text}
        """

        # Add extracted financial data if available
        if financial_data and financial_data.get("years"):
            # Format the financial data as a structured section
            prompt += "\n\nEXTRACTED FINANCIAL DATA:\n"

            # Add years
            years = financial_data.get("years", [])
            prompt += f"Years: {', '.join(map(str, years))}\n\n"

            # Add the most recent year's data
            if years:
                latest_year = max(years)
                prompt += f"Data for {latest_year}:\n"

                # Add balance sheet summary
                if latest_year in financial_data.get("balance_sheet", {}):
                    balance_sheet = financial_data["balance_sheet"][latest_year]
                    prompt += "Balance Sheet Summary:\n"

                    # Current Assets
                    if "Current Assets" in balance_sheet and "Total Current Assets" in balance_sheet["Current Assets"]:
                        prompt += f"- Total Current Assets: {balance_sheet['Current Assets']['Total Current Assets']}\n"

                    # Non-Current Assets
                    if "Non-Current Assets" in balance_sheet and "Total Non-Current Assets" in balance_sheet["Non-Current Assets"]:
                        prompt += f"- Total Non-Current Assets: {balance_sheet['Non-Current Assets']['Total Non-Current Assets']}\n"

                    # Current Liabilities
                    if "Current Liabilities" in balance_sheet and "Total Current Liabilities" in balance_sheet["Current Liabilities"]:
                        prompt += f"- Total Current Liabilities: {balance_sheet['Current Liabilities']['Total Current Liabilities']}\n"

                    # Non-Current Liabilities
                    if "Non-Current Liabilities" in balance_sheet and "Total Non-Current Liabilities" in balance_sheet["Non-Current Liabilities"]:
                        prompt += f"- Total Non-Current Liabilities: {balance_sheet['Non-Current Liabilities']['Total Non-Current Liabilities']}\n"

                    # Equity
                    if "Equity" in balance_sheet and "Total Equity" in balance_sheet["Equity"]:
                        prompt += f"- Total Equity: {balance_sheet['Equity']['Total Equity']}\n"

                # Add income statement summary
                if latest_year in financial_data.get("income_statement", {}):
                    income_statement = financial_data["income_statement"][latest_year]
                    prompt += "\nIncome Statement Summary:\n"

                    # Revenue
                    if "Revenue" in income_statement and "Total Revenue" in income_statement["Revenue"]:
                        prompt += f"- Total Revenue: {income_statement['Revenue']['Total Revenue']}\n"

                    # Net Income
                    if "Profit" in income_statement and "Net Income" in income_statement["Profit"]:
                        prompt += f"- Net Income: {income_statement['Profit']['Net Income']}\n"

                # Add cash flow summary
                if latest_year in financial_data.get("cash_flow", {}):
                    cash_flow = financial_data["cash_flow"][latest_year]
                    prompt += "\nCash Flow Summary:\n"

                    # Operating Cash Flow
                    if "Operating Activities" in cash_flow and "Net Cash from Operating Activities" in cash_flow["Operating Activities"]:
                        prompt += f"- Net Cash from Operating Activities: {cash_flow['Operating Activities']['Net Cash from Operating Activities']}\n"

                    # Investing Cash Flow
                    if "Investing Activities" in cash_flow and "Net Cash from Investing Activities" in cash_flow["Investing Activities"]:
                        prompt += f"- Net Cash from Investing Activities: {cash_flow['Investing Activities']['Net Cash from Investing Activities']}\n"

                    # Financing Cash Flow
                    if "Financing Activities" in cash_flow and "Net Cash from Financing Activities" in cash_flow["Financing Activities"]:
                        prompt += f"- Net Cash from Financing Activities: {cash_flow['Financing Activities']['Net Cash from Financing Activities']}\n"

                # Add key financial ratios
                if latest_year in financial_data.get("ratios", {}):
                    ratios = financial_data["ratios"][latest_year]
                    prompt += "\nKey Financial Ratios:\n"

                    # Liquidity ratios
                    if "Liquidity" in ratios:
                        for ratio_name, ratio_value in ratios["Liquidity"].items():
                            if ratio_value is not None:
                                prompt += f"- {ratio_name}: {ratio_value}\n"

                    # Solvency ratios
                    if "Solvency" in ratios:
                        for ratio_name, ratio_value in ratios["Solvency"].items():
                            if ratio_value is not None:
                                prompt += f"- {ratio_name}: {ratio_value}\n"

                    # Profitability ratios
                    if "Profitability" in ratios:
                        for ratio_name, ratio_value in ratios["Profitability"].items():
                            if ratio_value is not None:
                                prompt += f"- {ratio_name}: {ratio_value}\n"

        # Add instructions for the memo
        prompt += """

        Please analyze this document and create a comprehensive credit memo that includes:

        1. Executive Summary
        2. Financial Highlights (Revenue, EBITDA, Cash Flow, etc.)
        3. Key Ratios (Debt/Equity, Interest Coverage, etc.)
        4. Risk Analysis & Commentary
        5. Final Credit Recommendation

        Format your response as a well-structured credit memo that could be presented to a credit committee.
        Use the extracted financial data provided above to enhance your analysis, but also incorporate any additional insights from the document text.
        """

        return prompt

# Singleton instance for easy import
financial_analyzer = FinancialAnalyzer()
