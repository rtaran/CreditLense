# 💼 AI-Powered Credit Memo Co-Pilot Web App

# CreditLense: “From Data to Memo — In Seconds. Invest your time in decision-making, not data crunching”

A web-based application that allows clients to upload a **PDF financial statement** (or provide a link to one), which is then processed and analyzed using AI. The output is a **professionally formatted Credit Memo** generated as a downloadable **.docx (Word)** file.

---

## 🌐 Live App Overview

**What it does:**

1. 📤 Upload or link to a company’s financial PDF.
2. 🧠 Extract and analyze the content using an LLM (e.g., GPT-4, Gemini, etc.).
3. 📄 Generate a customized **Credit Memo** in Microsoft Word format.
4. ⬇️ Client downloads the memo in a clean, structured template.

---

## 🎯 Target Users

- Credit analysts & underwriters  
- Investors & VCs  
- Fintech credit risk teams  
- Accountants & consultants
- Auditors

---

## 🧠 App Highlights

- ✨ **Modern web interface** built with FastAPI, Jinja2, and responsive design
- 📱 Mobile-friendly UI with intuitive navigation
- 📥 PDF upload with company name customization
- 🧠 AI-driven extraction and interpretation of key financial data
- 🤖 Support for multiple LLM providers (OpenAI and Google Gemini) with ability to choose and compare results
- 📊 Customizable methodology stored in a prompt file
- 📄 Word document output using `python-docx`
- 🔄 Background processing for long-running tasks
- 📋 Document and memo management with interactive tables

---

## 🗂️ Project Structure

📁 CreditLense/
│
├── app/
│   ├── routers/
│   │   ├── documents.py          # Document upload and management
│   │   └── memos.py              # Memo generation and management
│   ├── main.py                   # FastAPI app entry point
│   ├── models.py                 # Database models
│   ├── database.py               # Database connection
│   ├── analyzer.py               # LLM-based analysis logic
│   ├── formatter.py              # Generates .docx memo
│   └── llm_service.py            # LLM service (OpenAI/Gemini)
│
├── config/                       # Configuration files
│   ├── .env.template             # Example environment file
│   └── pytest.ini                # PyTest configuration
│
├── data/                         # Data storage
│   ├── database/                 # Database files
│   │   └── credit_lense.db       # SQLite database
│   ├── output/                   # Generated memos
│   └── uploads/                  # Uploaded files
│
├── docs/                         # Documentation
│   └── next.md                   # Future development plans
│
├── documents/                    # Sample documents
│   ├── company/
│   └── methodology/
│
├── scripts/                      # Shell scripts
│   ├── run.sh                    # Script to run the app
│   └── run_tests.sh              # Script to run tests
│
├── static/                       # Static assets
│   ├── css/
│   │   └── styles.css            # Main stylesheet
│   ├── js/
│   │   └── main.js               # JavaScript for interactivity
│   └── favicon.ico               # Site favicon
│
├── templates/                    # Jinja2 HTML templates
│   ├── index.html                # Home page
│   ├── upload.html               # Document upload page
│   ├── documents.html            # Document management page
│   └── memos.html                # Memo management page
│
├── tests/                        # Test files
│   ├── integration/              # Integration tests
│   └── unit/                     # Unit tests
│
├── pyproject.toml                # Python dependency and tool config (uv)
├── .env                          # Environment variables (not in version control)
└── README.md                     # Project documentation

---

## ⚙️ Setup Instructions

```bash
git clone https://github.com/rtaran/credit_lense.git
cd credit_lense
pip install uv
uv init
uv sync
uv lock
cp config/.env.template .env  # Create .env file from template
# Edit .env file to add your API keys
./scripts/run.sh
```

⚠️ Make sure the `.env` file exists in the root directory. You can use the included `config/.env.template` as a starting point.

### Environment Variables

The application uses the following environment variables:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `OPENAI_API_KEY` | Your OpenAI API key for accessing GPT models | - |
| `GOOGLE_API_KEY` | Your Google API key for accessing Gemini models | - |
| `NEWS_API_KEY` | Your News API key for fetching news (optional) | - |
| `DATABASE_URL` | URL for the SQLite database | `sqlite:///./database/financial_data.db` |
| `UPLOAD_FOLDER` | Directory for uploaded files | `./data/uploads` |
| `LLM_PROVIDER` | Comma-separated list of LLM providers to use | `google,openai` |
| `STATIC_FILES_DIR` | Directory for static files | `static` |
| `TEMPLATES_DIR` | Directory for HTML templates | `templates` |

You can set these variables in the `.env` file:

```
# API Keys
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key

# Database Configuration
DATABASE_URL=sqlite:///./database/financial_data.db

# Upload Configuration
UPLOAD_FOLDER=./data/uploads

# LLM Configuration
LLM_PROVIDER=openai,google  # comma-separated list of providers

# Directory Configuration
STATIC_FILES_DIR=static
TEMPLATES_DIR=templates
```

## 📋 How to Use

Once you have set up the application and started the server using `./scripts/run.sh`, you can access the web interface by opening your browser and navigating to `http://localhost:5001`.

### 1. Upload a Financial Document

1. From the home page, click on "Upload Document" or navigate to the "Documents" section.
2. Click the "Choose File" button and select a PDF financial statement.
3. Enter the company name (optional but recommended).
4. Click "Upload" to submit the document.
5. The system will process the document and extract financial data.

### 2. Generate a Credit Memo

1. Navigate to the "Documents" section to see your uploaded documents.
2. Find the document you want to analyze and click "Generate Memo".
3. Select the LLM provider you want to use (OpenAI or Google Gemini).
4. Click "Generate" to start the analysis process.
5. The system will process the document in the background. This may take a few moments depending on the size of the document and the LLM provider's response time.

### 3. View and Download Memos

1. Navigate to the "Memos" section to see all generated memos.
2. You can view a memo directly in the browser by clicking "View".
3. To download the memo as a Word document, click "Download".
4. The memo will be downloaded as a .docx file that can be opened in Microsoft Word or any compatible word processor.

### 4. Managing Documents and Memos

1. In the "Documents" section, you can delete documents by clicking the "Delete" button.
2. In the "Memos" section, you can delete memos by clicking the "Delete" button.
3. You can generate multiple memos for the same document using different LLM providers to compare results.

### 5. Uploading Methodology Documents

1. Navigate to the "Methodology" section.
2. Upload a PDF document containing your credit analysis methodology.
3. The system will use this methodology to guide the LLM in generating more accurate and relevant credit memos.

### 6. Customizing Memo Format

1. Navigate to the "Memo Format" section.
2. Upload a Word document (.docx) template for your credit memos.
3. The system will use this template when generating new memos, maintaining your organization's branding and formatting standards.

🧾 Output Example

The credit memo generated by the app includes:
	•	Executive Summary
	•	Financial Highlights (Revenue, EBITDA, Cash Flow, etc.)
	•	Key Ratios (Debt/Equity, Interest Coverage, etc.)
	•	Risk Analysis & Commentary
	•	Final Credit Recommendation

📄 Exported as: credit_memo_<company_name>.docx

## 🧪 Testing

The application includes a comprehensive test suite covering both unit tests and integration tests. The tests ensure that all components of the application work correctly and that the API endpoints behave as expected.

### Running Tests

To run the tests, use the provided script:

```bash
./scripts/run_tests.sh
```

This will run all tests and generate a coverage report in the `test_reports/coverage` directory.

For more information about the tests, see the [tests/README.md](tests/README.md) file.

🖼️ UI Preview

The application now features a complete, responsive front-end with:

- Modern, clean design with intuitive navigation
- Mobile-friendly interface that works on all devices
- Interactive document and memo management
- Real-time feedback for user actions
- Seamless integration with the API endpoints

(Screenshots will be added soon)

🛣️ Roadmap
	•	Add email delivery of memos
	•	Dashboard for past uploads
	•	OCR support for scanned PDFs
	•	Multiple languages (EN/DE/FR)
	•	Role-based access control

⸻

🤝 Contributing

We’re open to collaboration! Create an issue or submit a pull request.

⸻

📬 Contact

For questions or enterprise features, reach out:
📧 info@tarantech.eu
