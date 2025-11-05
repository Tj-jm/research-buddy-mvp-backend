import base64, pandas as pd
from typing import List, Dict, Any

ORDER = [
    "Professor Name",
    "Designation",
    "University Name",
    "Email",
    "Profile Link",
    "Hook Point",
    "Research Interests",
    "Personal Website",
    "Google Scholar",
    "Bio",
    "Source",
    "Subject",
]

KEYMAP = {
    "professor_name": "Professor Name",
    "designation": "Designation",
    "university_name": "University Name",
    "email": "Email",
    "profile_link": "Profile Link",
    "hook_point": "Hook Point",
    "research_interests": "Research Interests",
    "personal_website": "Personal Website",
    "google_scholar": "Google Scholar",
    "bio": "Bio",
    "source": "Source",
    "subject": "Subject",
}

SUBJECT_FALLBACK = {
    "ai": "AI/ML",
    "machine learning": "AI/ML",
    "deep learning": "AI/ML",
    "nlp": "AI/ML",
    "natural language": "AI/ML",
    "robot": "AI/ML",
    "education": "Education & Leadership",
    "learning science": "Education & Leadership",
    "pedagogy": "Education & Leadership",
    "leadership": "Education & Leadership",
    "data": "Data Science",
    "statistics": "Data Science",
    "analytics": "Data Science",
    "visualization": "Data Science",
}

def normalize_record(d: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Map known snake_case keys → aliases
    mapped = {KEYMAP.get(k, k): v for k, v in d.items()}

    # 2. Ensure ordered schema, but keep any extra keys
    out = {}
    for k in ORDER:
        out[k] = mapped.get(k)

    # 3. Add back any leftover keys not in ORDER
    for k, v in mapped.items():
        if k not in ORDER:
            out[k] = v

    # 4. Subject fallback if missing
    if not out.get("Subject"):
        corpus = " ".join([
            str(out.get("Research Interests") or ""),
            str(out.get("Hook Point") or ""),
            str(out.get("Bio") or "")
        ]).lower()
        for kw, subj in SUBJECT_FALLBACK.items():
            if kw in corpus:
                out["Subject"] = subj
                break
        else:
            out["Subject"] = "Data Science"

    return out

def to_csv_base64(rows: List[Dict[str, Any]]) -> tuple[str, str]:
    df = pd.DataFrame(rows)

    # Reorder if possible
    cols = [c for c in ORDER if c in df.columns]
    other_cols = [c for c in df.columns if c not in ORDER]
    df = df[cols + other_cols]

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    b64 = base64.b64encode(csv_bytes).decode("utf-8")
    return ("faculty_profiles.csv", b64)
