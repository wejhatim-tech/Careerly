import os
import json
import requests
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
MODEL = 'gemini-3.8-flash'

JSEARCH_URL = 'https://jsearch.p.rapidapi.com'
JSEARCH_HEADERS = {
    'X-RapidAPI-Key': os.getenv('RAPIDAPI_KEY'),
    'X-RapidAPI-Host': 'jsearch.p.rapidapi.com',
}


# Send a prompt to Gemini and return the text answer
def ask_ai(prompt):
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        return response.text
    except Exception:
        return None


# Turn the AI text answer into a Python list / dict
def parse_json(text):
    if not text:
        return None
    text = text.replace('```json', '').replace('```', '').strip()
    start = min([i for i in (text.find('['), text.find('{')) if i != -1], default=-1)
    end = max(text.rfind(']'), text.rfind('}'))
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except ValueError:
        return None


# Keep only the job fields we need
def clean_job(job):
    city = job.get('job_city') or ''
    country = job.get('job_country') or ''
    return {
        'job_id': job.get('job_id'),
        'title': job.get('job_title'),
        'company': job.get('employer_name'),
        'location': ', '.join(part for part in [city, country] if part),
        'employment_type': job.get('job_employment_type'),
        'is_remote': job.get('job_is_remote'),
        'description': job.get('job_description') or '',
        'apply_link': job.get('job_apply_link'),
    }

# Country codes for the user's preferred location
COUNTRY_CODES = {
    'palestine': 'ps', 'jordan': 'jo', 'amman': 'jo',
    'saudi': 'sa', 'riyadh': 'sa', 'uae': 'ae', 'dubai': 'ae',
    'qatar': 'qa', 'kuwait': 'kw', 'egypt': 'eg',
    'usa': 'us', 'uk': 'gb', 'germany': 'de', 'canada': 'ca',
}


def get_country_code(location):
    location = (location or '').lower()
    for name, code in COUNTRY_CODES.items():
        if name in location:
            return code
    return 'jo'



# Search live jobs from Google for Jobs (JSearch API)
def search_jobs(query, country='jo', num=10):
    try:
        response = requests.get(
            f'{JSEARCH_URL}/search-v2',
            headers=JSEARCH_HEADERS,
            params={'query': query, 'num_pages': 1, 'country': country},
            timeout=20,
        )
        data = response.json().get('data', [])
        if isinstance(data, dict):
            data = data.get('jobs', [])
        return [clean_job(job) for job in data[:num]]
    except Exception as e:
        print('JSearch error:', e)
        return []


# Get one job by its id (for the Job Details page)
def get_job(job_id):
    try:
        response = requests.get(
            f'{JSEARCH_URL}/job-details',
            headers=JSEARCH_HEADERS,
            params={'job_id': job_id},
            timeout=20,
        )
        jobs = response.json().get('data', [])
        return clean_job(jobs[0]) if jobs else None
    except Exception:
        return None
        

# Ask Gemini to pick the best 5 jobs for this profile
def match_jobs(profile, skills, jobs):
    if not jobs:
        return []

    short_jobs = [
        {'index': i, 'title': j['title'], 'company': j['company'],
        'location': j['location'], 'description': j['description'][:600]}
        for i, j in enumerate(jobs)
    ]
    prompt = f"""
You are a career coach. Pick the best 5 jobs for this candidate.

Candidate:
- Target role: {profile.target_role}
- Career level: {profile.career_level}
- Years of experience: {profile.years_experience}
- Preferred location: {profile.preferred_location}
- Work mode: {profile.work_mode}
- Employment type: {profile.employment_type}
- Skills: {', '.join(skills)}

Jobs (JSON):
{json.dumps(short_jobs)}

Return ONLY a JSON list, best match first, like:
[{{"index": 0, "match": "Excellent", "reason": "one short sentence"}}]
match must be one of: Excellent, Good, Possible.
"""
    result = parse_json(ask_ai(prompt)) or []

    best = []
    for item in result[:5]:
        i = item.get('index')
        if isinstance(i, int) and 0 <= i < len(jobs):
            job = dict(jobs[i])
            job['match'] = item.get('match', 'Possible')
            job['reason'] = item.get('reason', '')
            best.append(job)
    return best        