import pytest
from app.models import CompanyData, FinancialMemo

def test_company_data_model(db_session):
    """Test creating, reading, updating, and deleting a CompanyData record."""
    # Create a new company data record
    company_data = CompanyData(
        pdf_file_name="test_file.pdf",
        pdf_string="This is a test PDF content",
        company_name="Test Company",
        total_assets=1000000.0,
        total_liabilities=500000.0,
        revenue=2000000.0,
        net_income=300000.0
    )
    
    # Add to the database
    db_session.add(company_data)
    db_session.commit()
    
    # Verify it was added with an ID
    assert company_data.document_id is not None
    
    # Retrieve the record
    retrieved_data = db_session.query(CompanyData).filter_by(document_id=company_data.document_id).first()
    assert retrieved_data is not None
    assert retrieved_data.pdf_file_name == "test_file.pdf"
    assert retrieved_data.company_name == "Test Company"
    assert retrieved_data.total_assets == 1000000.0
    
    # Update the record
    retrieved_data.company_name = "Updated Company"
    db_session.commit()
    
    # Verify the update
    updated_data = db_session.query(CompanyData).filter_by(document_id=company_data.document_id).first()
    assert updated_data.company_name == "Updated Company"
    
    # Delete the record
    db_session.delete(updated_data)
    db_session.commit()
    
    # Verify it was deleted
    deleted_data = db_session.query(CompanyData).filter_by(document_id=company_data.document_id).first()
    assert deleted_data is None

def test_financial_memo_model(db_session, sample_document):
    """Test creating, reading, updating, and deleting a FinancialMemo record."""
    # Create a new financial memo record
    memo = FinancialMemo(
        document_id=sample_document.document_id,
        memo_string="This is a test memo",
        file_path="./output/test_memo.docx",
        llm_provider="google"
    )
    
    # Add to the database
    db_session.add(memo)
    db_session.commit()
    
    # Verify it was added with an ID
    assert memo.memo_id is not None
    
    # Retrieve the record
    retrieved_memo = db_session.query(FinancialMemo).filter_by(memo_id=memo.memo_id).first()
    assert retrieved_memo is not None
    assert retrieved_memo.memo_string == "This is a test memo"
    assert retrieved_memo.document_id == sample_document.document_id
    assert retrieved_memo.llm_provider == "google"
    
    # Update the record
    retrieved_memo.memo_string = "Updated memo content"
    retrieved_memo.llm_provider = "openai"
    db_session.commit()
    
    # Verify the update
    updated_memo = db_session.query(FinancialMemo).filter_by(memo_id=memo.memo_id).first()
    assert updated_memo.memo_string == "Updated memo content"
    assert updated_memo.llm_provider == "openai"
    
    # Delete the record
    db_session.delete(updated_memo)
    db_session.commit()
    
    # Verify it was deleted
    deleted_memo = db_session.query(FinancialMemo).filter_by(memo_id=memo.memo_id).first()
    assert deleted_memo is None

def test_relationship_between_models(db_session):
    """Test the relationship between CompanyData and FinancialMemo."""
    # Create a company data record
    company_data = CompanyData(
        pdf_file_name="relationship_test.pdf",
        pdf_string="Testing relationships",
        company_name="Relationship Test Co"
    )
    db_session.add(company_data)
    db_session.commit()
    
    # Create multiple memos for the same document
    memo1 = FinancialMemo(
        document_id=company_data.document_id,
        memo_string="First memo",
        llm_provider="google"
    )
    
    memo2 = FinancialMemo(
        document_id=company_data.document_id,
        memo_string="Second memo",
        llm_provider="openai"
    )
    
    db_session.add_all([memo1, memo2])
    db_session.commit()
    
    # Query all memos for the document
    memos = db_session.query(FinancialMemo).filter_by(document_id=company_data.document_id).all()
    
    # Verify we have two memos for the document
    assert len(memos) == 2
    assert memos[0].document_id == company_data.document_id
    assert memos[1].document_id == company_data.document_id
    
    # Verify different providers
    providers = [memo.llm_provider for memo in memos]
    assert "google" in providers
    assert "openai" in providers