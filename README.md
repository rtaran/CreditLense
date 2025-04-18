# 💼 AI-Powered Credit Memo Web App

# CreditLense: “From Data to Memo — In Seconds.”

A web-based application that allows clients to upload a **PDF financial statement** (or provide a link to one), which is then processed and analyzed using AI. The output is a **professionally formatted Credit Memo** generated as a downloadable **.docx (Word)** file.

---

## 🌐 Live App Overview

**What it does:**

1. 📤 Upload or link to a company’s financial PDF.
2. 🧠 Extract and analyze the content using an LLM (e.g., GPT-4).
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

- ✨ **Simple web interface** built with Flask / Streamlit / FastAPI
- 📥 PDF upload or link input supported
- 🧠 AI-driven extraction and interpretation of key financial data
- 📊 Customizable methodology stored in a prompt file
- 📄 Word document output using `python-docx`

---

## 🗂️ Project Structure

📁 ai_credit_memo_webapp/
│
├── app/
│   ├── templates/
│   │   └── upload.html            # Upload form UI
│   ├── static/                    # CSS and assets
│   ├── routes.py                 # Flask routes and logic
│   ├── extractor.py              # PDF text extractor
│   ├── analyzer.py               # LLM-based analysis logic
│   ├── formatter.py              # Generates .docx memo
│   └── utils.py                  # Link downloading, cleanup, etc.
│
├── prompts/
│   └── credit_memo_prompt.txt    # AI instructions
│
├── output/
│   └── credit_memo_.docx
│
├── app.py                        # Main app entry
├── requirements.txt
└── README.md

---

## ⚙️ Setup Instructions

```bash
# Clone and enter the project
git clone https://github.com/yourusername/ai-credit-memo-webapp.git
cd ai-credit_memo_webapp

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the web app
python app.py
```
OPENAI_API_KEY=your_openai_key
UPLOAD_FOLDER=./output

🧾 Output Example

The credit memo generated by the app includes:
	•	Executive Summary
	•	Financial Highlights (Revenue, EBITDA, Cash Flow, etc.)
	•	Key Ratios (Debt/Equity, Interest Coverage, etc.)
	•	Risk Analysis & Commentary
	•	Final Credit Recommendation

📄 Exported as: credit_memo_<company_name>.docx

🖼️ UI Preview

(optional: insert screenshot here)

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
