from sqlalchemy import Column, Integer, String, Float, Text, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel

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
    
class CompanyDataReturnModel(BaseModel):

    company_name = Column(String, nullable=True)
    reporting_period = Column(Date, nullable=True)
    total_assets = Column(Float, nullable=True)
    total_liabilities = Column(Float, nullable=True)
    revenue = Column(Float, nullable=True)
    net_income = Column(Float, nullable=True)
    cash_flow = Column(Float, nullable=True)
    industry = Column(String, nullable=True)
    additional_notes = Column(Text, nullable=True)

class FinancialMemo(Base):
    __tablename__ = "financial_memos"

    memo_id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("company_data.document_id"))
    memo_string = Column(Text)