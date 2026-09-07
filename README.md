# AI Resume Screener & Job Matcher - Python FastAPI Backend Guide

This backend is designed specifically for beginner developers learning how to integrate **FastAPI**, **PyPDF2**, and **Google Gemini AI (`google-genai`)** into an ATS (Applicant Tracking System) resume analyzer.

---

## 🚀 How to Run the Python Backend Locally

### 1. Create a Virtual Environment
```bash
python -m venv venv
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Your Gemini API Key
```bash
export GEMINI_API_KEY="your_api_key_here"
# On Windows CMD:
set GEMINI_API_KEY="your_api_key_here"
# On Windows PowerShell:
$env:GEMINI_API_KEY="your_api_key_here"
```

### 4. Start the FastAPI Server
```bash
uvicorn main:app --reload --port 8000
```

### 5. Interactive API Documentation
Open your browser at [http://localhost:8000/docs](http://localhost:8000/docs) to access the auto-generated Swagger UI where you can test file uploads and check responses!

---

## 🔍 How the Code Works Step-by-Step

1. **`extract_text_from_pdf(file_bytes)`**:
   Uses `PyPDF2.PdfReader` to iterate through every page of the uploaded PDF and extract plain text. Includes safeguards for encrypted/corrupted files.

2. **`POST /api/analyze`**:
   - Uses `UploadFile` to stream the PDF directly into memory.
   - Extracts resume text and validates the minimum length of the job description.
   - Calls Gemini (`gemini-3.8-flash`) with structured output instructions asking for:
     - `match_score` (0-100)
     - `matching_skills` (list of skills that match)
     - `missing_skills` (skills from JD missing in resume)
     - `improvement_suggestions` (3-4 bullet points to improve the resume)
   - Validates the output through the `AnalysisResponse` Pydantic model.
