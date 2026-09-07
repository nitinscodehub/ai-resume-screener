# main.py - AI Resume Screener & Job Matcher
# Built with FastAPI + PyPDF2 + Google Gemini

import os
import io
import json
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import PyPDF2

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

app = FastAPI(title="Resume Screener API")

# cors setup so frontend can talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# response schema
class MatchResult(BaseModel):
    job_title: str
    candidate_name: Optional[str] = "Candidate"
    match_score: int
    score_verdict: Optional[str] = "Good Match"
    matching_skills: List[str]
    missing_skills: List[str]
    improvement_suggestions: List[str]
    summary: str
    strengths: Optional[List[str]] = []


# helper to pull text from pdf using pypdf2
def parse_pdf(data: bytes) -> str:
    try:
        buffer = io.BytesIO(data)
        pdf_reader = PyPDF2.PdfReader(buffer)

        # check if it has a password
        if pdf_reader.is_encrypted:
            try:
                pdf_reader.decrypt("")
            except Exception:
                raise HTTPException(status_code=400, detail="PDF is password protected!")

        extracted = ""
        for p in pdf_reader.pages:
            t = p.extract_text()
            if t:
                extracted += t + "\n"

        # TODO: what if it's a scanned pdf image? Need OCR (pytesseract or pdf2image) later
        return extracted.strip()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to read PDF file: {str(e)}")


@app.get("/")
def home():
    return {"message": "Resume Screener API is running"}


# main route to scan resume
@app.post("/api/analyze", response_model=MatchResult)
async def analyze_resume(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    job_title: Optional[str] = Form("")
):
    # make sure file is a pdf
    if not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file!")

    job_desc = job_description.strip()
    if len(job_desc) < 10:
        raise HTTPException(status_code=400, detail="Job description is too short!")

    # read the bytes
    pdf_bytes = await resume.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty!")

    resume_text = parse_pdf(pdf_bytes)

    # get gemini api key from env
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is missing in env vars")

    # TODO: maybe cache results in sqlite so we don't re-call gemini on same file

    try:
        ai_client = genai.Client(api_key=key)

        user_prompt = f"""
Compare this resume with the job description.

Job Title: {job_title if job_title else "Detect from job description"}
Job Description:
{job_desc}

Resume Text:
{resume_text if resume_text else "Read text from document"}

Give me JSON back with:
- job_title: string
- candidate_name: string
- match_score: number between 0 and 100
- score_verdict: string (like High Match, Moderate Match, or Low Match)
- matching_skills: list of matching skills
- missing_skills: list of important skills missing in resume
- improvement_suggestions: 3-4 bullet points to improve resume
- summary: 2 sentences overview
- strengths: list of 2-3 strengths
"""

        gemini_resp = ai_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        res_json = json.loads(gemini_resp.text)
        score_val = int(res_json.get("match_score", 0))

        return MatchResult(
            job_title=res_json.get("job_title") or job_title or "Target Role",
            candidate_name=res_json.get("candidate_name", "Candidate"),
            match_score=max(0, min(100, score_val)),
            score_verdict=res_json.get("score_verdict") or ("Strong Match" if score_val >= 75 else "Needs Work"),
            matching_skills=res_json.get("matching_skills", []),
            missing_skills=res_json.get("missing_skills", []),
            improvement_suggestions=res_json.get("improvement_suggestions", []),
            summary=res_json.get("summary", "Done scanning."),
            strengths=res_json.get("strengths", [])
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(err)}")


if __name__ == "__main__":
    import uvicorn
    # run with: python main.py
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
