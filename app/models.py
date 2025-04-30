from sqlalchemy import Column, Integer, String, Float, Text, Date, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class CompanyData(Base):
    __tablename__ = "company_data"

    document_id = Column(Integer, primary_key=True, index=True)
    pdf_file_name = Column(String)
    pdf_string = Column(Text)

    company_name = Column(String, nullable=True)
    reporting_period = Column(Date, nullable=True)
    total_assets = Column(Float, nullable=True)
    total_liabilities = Column(Float, nullable=True)
    revenue = Column(Float, nullable=True)
    net_income = Column(Float, nullable=True)
    cash_flow = Column(Float, nullable=True)
    industry = Column(String, nullable=True)
    additional_notes = Column(Text, nullable=True)

    # Relationships
    financial_years = relationship("FinancialYear", back_populates="company", cascade="all, delete-orphan")
    memos = relationship("FinancialMemo", back_populates="company", cascade="all, delete-orphan")

class FinancialYear(Base):
    __tablename__ = "financial_years"

    year_id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("company_data.document_id"))
    year = Column(Integer, nullable=False)  # e.g., 2023

    # Relationships
    company = relationship("CompanyData", back_populates="financial_years")
    balance_sheet_items = relationship("BalanceSheetItem", back_populates="financial_year", cascade="all, delete-orphan")
    income_statement_items = relationship("IncomeStatementItem", back_populates="financial_year", cascade="all, delete-orphan")
    cash_flow_items = relationship("CashFlowItem", back_populates="financial_year", cascade="all, delete-orphan")
    financial_ratios = relationship("FinancialRatio", back_populates="financial_year", cascade="all, delete-orphan")

class BalanceSheetItem(Base):
    __tablename__ = "balance_sheet_items"

    item_id = Column(Integer, primary_key=True, index=True)
    year_id = Column(Integer, ForeignKey("financial_years.year_id"))
    item_name = Column(String, nullable=False)  # e.g., "Cash and Cash Equivalents"
    item_value = Column(Float, nullable=True)
    item_category = Column(String, nullable=True)  # e.g., "Current Assets", "Non-Current Assets", "Current Liabilities", etc.

    # Relationship
    financial_year = relationship("FinancialYear", back_populates="balance_sheet_items")

class IncomeStatementItem(Base):
    __tablename__ = "income_statement_items"

    item_id = Column(Integer, primary_key=True, index=True)
    year_id = Column(Integer, ForeignKey("financial_years.year_id"))
    item_name = Column(String, nullable=False)  # e.g., "Revenue", "Cost of Goods Sold", "Operating Expenses", etc.
    item_value = Column(Float, nullable=True)
    item_category = Column(String, nullable=True)  # e.g., "Revenue", "Expenses", "Profit", etc.

    # Relationship
    financial_year = relationship("FinancialYear", back_populates="income_statement_items")

class CashFlowItem(Base):
    __tablename__ = "cash_flow_items"

    item_id = Column(Integer, primary_key=True, index=True)
    year_id = Column(Integer, ForeignKey("financial_years.year_id"))
    item_name = Column(String, nullable=False)  # e.g., "Cash Flow from Operations", "Cash Flow from Investing", etc.
    item_value = Column(Float, nullable=True)
    item_category = Column(String, nullable=True)  # e.g., "Operating Activities", "Investing Activities", "Financing Activities", etc.

    # Relationship
    financial_year = relationship("FinancialYear", back_populates="cash_flow_items")

class FinancialRatio(Base):
    __tablename__ = "financial_ratios"

    ratio_id = Column(Integer, primary_key=True, index=True)
    year_id = Column(Integer, ForeignKey("financial_years.year_id"))
    ratio_name = Column(String, nullable=False)  # e.g., "Current Ratio", "Debt-to-Equity", "Return on Assets", etc.
    ratio_value = Column(Float, nullable=True)
    ratio_category = Column(String, nullable=True)  # e.g., "Liquidity", "Solvency", "Profitability", etc.

    # Relationship
    financial_year = relationship("FinancialYear", back_populates="financial_ratios")

class FinancialMemo(Base):
    __tablename__ = "financial_memos"

    memo_id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("company_data.document_id"))
    memo_string = Column(Text)
    file_path = Column(String, nullable=True)
    llm_provider = Column(String, nullable=True)

    # Relationship
    company = relationship("CompanyData", back_populates="memos")
