import pdfplumber
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz


def extract_text_from_pdf(file_obj) -> str:
    """Extract plain text from an uploaded PDF file object."""
    text_parts = []
    file_obj.seek(0)
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    file_obj.seek(0)
    return "\n".join(text_parts)


def compute_fit_score(cv_text: str, job_requirements: str) -> float:
    """
    TF-IDF + cosine similarity between a CV and a job's requirements text.
    Returns a score from 0-100.
    """
    if not cv_text.strip() or not job_requirements.strip():
        return 0.0

    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform([cv_text, job_requirements])
    except ValueError:
        # happens if vocabulary is empty after stop-word removal
        return 0.0

    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    return round(float(similarity) * 100, 2)


def is_duplicate_applicant(full_name: str, email: str, other_name: str, other_email: str, threshold: int = 90) -> bool:
    """
    Fuzzy-match names/emails to catch near-duplicate applicant accounts
    (e.g. slightly misspelled name, same email with different casing).
    """
    name_score = fuzz.ratio(full_name.lower().strip(), other_name.lower().strip())
    email_score = fuzz.ratio(email.lower().strip(), other_email.lower().strip())
    return name_score >= threshold or email_score >= threshold
