import fitz  # PyMuPDF
from docx import Document as DocxDocument
from pptx import Presentation
import io
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
from openai import AzureOpenAI
import json

load_dotenv()

class DocumentProcessor:
    def __init__(self):
        self.openai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2023-05-15",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )

    def extract_text(self, file_content: bytes, content_type: str) -> str:
        """Extract text from different document types."""
        if content_type == "application/pdf":
            return self._extract_from_pdf(file_content)
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return self._extract_from_docx(file_content)
        elif content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            return self._extract_from_pptx(file_content)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

    def _extract_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF file."""
        doc = fitz.open(stream=file_content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    def _extract_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file."""
        doc = DocxDocument(io.BytesIO(file_content))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text

    def _extract_from_pptx(self, file_content: bytes) -> str:
        """Extract text from PPTX file."""
        prs = Presentation(io.BytesIO(file_content))
        text = ""
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
        return text

    def check_compliance(self, text: str, rules: List[str]) -> Dict[str, Any]:
        """Check document text against compliance rules using Azure OpenAI."""
        prompt = f"""
        Analyze the following document text for compliance violations based on these rules:
        {', '.join(rules)}

        Document text:
        {text}

        Please identify any violations and provide:
        1. The specific text that violates the rule
        2. Which rule it violates
        3. A brief explanation of the violation
        4. Suggested fix

        Format the response as a JSON object with the following structure:
        {{
            "violations": [
                {{
                    "text": "violating text",
                    "rule": "violated rule",
                    "explanation": "explanation",
                    "suggestion": "suggested fix"
                }}
            ]
        }}
        """

        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a compliance expert analyzing financial documents."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )

        return response.choices[0].message.content 