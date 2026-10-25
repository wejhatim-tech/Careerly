import os
import json
import requests
import time
from pypdf import PdfReader
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(
    api_key=os.getenv('GEMINI_API_KEY'),
    http_options=types.HttpOptions(
        timeout=30000,
        retry_options=types.HttpRetryOptions(
            attempts=2
        )
    )
)
PRIMARY_MODEL = 'gemini-3.8-flash'
BACKUP_MODEL = 'gemini-3.6-flash'

JSEARCH_URL = 'https://jsearch.p.rapidapi.com'
JSEARCH_HEADERS = {
    'X-RapidAPI-Key': os.getenv('RAPIDAPI_KEY'),
    'X-RapidAPI-Host': 'jsearch.p.rapidapi.com',
}


# Send a prompt to Gemini and return the text answer
def ask_ai(prompt):
    try:
        response = client.models.generate_content(
            model=PRIMARY_MODEL,
            contents=prompt
        )

        return response.text

    except Exception as e:
        print('Primary Gemini error:', e)

    try:
        response = client.models.generate_content(
            model=BACKUP_MODEL,
            contents=prompt
        )

        return response.text

    except Exception as e:
        print('Backup Gemini error:', e)
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


def clean_job(job):
    city = job.get('job_city') or ''
    country = job.get('job_country') or ''
    location = job.get('job_location') or ''

    if not location:
        location = ', '.join(
            part
            for part in [city, country]
            if part
        )

    return {
        'job_id': job.get('job_id'),
        'title': job.get('job_title'),
        'company': job.get('employer_name'),
        'location': location,
        'country': country,
        'employment_type': job.get(
            'job_employment_type'
        ),
        'is_remote': job.get('job_is_remote'),
        'description': (
            job.get('job_description') or ''
        ),
        'apply_link': job.get('job_apply_link'),
        'expiration_timestamp': job.get(
            'job_offer_expiration_timestamp'
        ),
    }
    # Country codes for the user's preferred location
COUNTRY_CODES = {
    'palestine': 'ps',
    'west bank': 'ps',
    'jordan': 'jo',
    'amman': 'jo',
    'saudi': 'sa',
    'riyadh': 'sa',
    'uae': 'ae',
    'dubai': 'ae',
    'qatar': 'qa',
    'kuwait': 'kw',
    'egypt': 'eg',
    'usa': 'us',
    'united states': 'us',
    'uk': 'gb',
    'united kingdom': 'gb',
    'germany': 'de',
    'canada': 'ca',
}


def get_country_code(location):
    location = (location or '').lower()

    for name, code in COUNTRY_CODES.items():
        if name in location:
            return code

    return 'jo'



def search_jobs(query, country=None, num=10, remote=False):
    try:
        params = {
            'query': query,
            'num_pages': 1,
            'date_posted': 'month'
        }

        # Add country when searching in a specific country
        if country:
            params['country'] = country

        # Only return remote jobs when remote is requested
        if remote:
            params['work_from_home'] = True

        response = None

        for attempt in range(2):
            try:
                response = requests.get(
                    f'{JSEARCH_URL}/search-v2',
                    headers=JSEARCH_HEADERS,
                    params=params,
                    timeout=15,
                )

                response.raise_for_status()
                break

            except requests.RequestException as e:
                print(
                    f'JSearch attempt {attempt + 1} failed:',
                    e
                )
                response = None

        if response is None:
            return []

        data = response.json().get('data', {})

        jobs = (
            data.get('jobs', [])
            if isinstance(data, dict)
            else data
        )

        valid_jobs = []
        current_time = int(time.time())

        for job in jobs:
            cleaned_job = clean_job(job)

            # Skip jobs without an application link
            if not cleaned_job.get('apply_link'):
                continue

            expiration = cleaned_job.get(
                'expiration_timestamp'
            )

            # Skip expired jobs
            if expiration and expiration < current_time:
                continue

            valid_jobs.append(cleaned_job)

            if len(valid_jobs) >= num:
                break

        return valid_jobs

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

    # 1. Filter wrong career levels BEFORE sending jobs to Gemini
    filtered_jobs = []

    for job in jobs:
        if career_level_match(profile.career_level, job['title']):
            filtered_jobs.append(job)

    jobs = filtered_jobs

    if not jobs:
        return []

    # 2. Prepare a shorter version of the jobs for Gemini
    short_jobs = [
        {
            'index': i,
            'title': job['title'],
            'company': job['company'],
            'location': job['location'],
            'is_remote': job['is_remote'],
            'description': job['description'][:800]
        }
        for i, job in enumerate(jobs)
    ]

    # 3. Career levels allowed for this user
    allowed_levels = get_allowed_levels(profile.career_level)

    prompt = f"""
You are a job matching assistant.

User profile:
Target role: {profile.target_role}
Career level: {profile.career_level}
Location: {profile.preferred_location}
Work mode: {profile.work_mode}
Employment type: {profile.employment_type}
Skills: {', '.join(skills) if skills else 'Not provided'}

Suitable career levels:
{", ".join(allowed_levels)}

Career level rules:
- Junior users: Junior, Entry-Level, New Grad, Graduate, or suitable Internship roles.
- Mid-level users: Mid-Level or Intermediate roles.
- Senior users: Senior or Lead roles.
- Never recommend Staff, Principal, Head, Director, or Manager roles unless they clearly match the user's career level.

Important matching rules:
- Match the target role.
- Match the career level.
- Respect the preferred work mode.
- Consider the user's skills.
- A remote job must be available for someone living in {profile.preferred_location}.
- Reject jobs that are restricted to another country, such as US-only or requiring US work authorization.
- Do not recommend a job only because it is remote.
- Do not recommend jobs clearly above or below the user's level.

Available jobs:
{json.dumps(short_jobs, indent=2)}

Choose up to 5 of the best matching jobs.

Return ONLY a JSON array in this exact format:

[
    {{
        "index": 0,
        "match": "Excellent",
        "reason": "Short explanation"
    }}
]

match must be one of: Excellent, Good, Possible.

"""

    ai_answer = ask_ai(prompt)

    # Temporary print so we can see what Gemini returned
    print("GEMINI RESPONSE:")
    print(ai_answer)

    result = parse_json(ai_answer)

    # 4. Fallback if Gemini fails
    # IMPORTANT: jobs were already filtered by career level above
    if not result:
        fallback_jobs = []

        for job in jobs:
            if profile.work_mode_list() == ['remote']:
                if not remote_location_match(profile.preferred_location, job):
                    continue

            fallback_job = dict(job)
            fallback_job['match'] = 'Possible'
            fallback_job['reason'] = ('This current job matches your career level and search criteria.')

            fallback_jobs.append(fallback_job)

            if len(fallback_jobs) >= 5:
                break

        return fallback_jobs

    # 5. Build final job results
    best = []

    for item in result[:5]:
        i = item.get('index')

        if isinstance(i, int) and 0 <= i < len(jobs):
            job = dict(jobs[i])

            # Final safety check
            if not career_level_match(profile.career_level, job['title']):
                continue

            job['match'] = item.get('match', 'Possible')
            job['reason'] = item.get('reason', '')
            best.append(job)

    return best

def get_allowed_levels(career_level):
    level = career_level.lower()

    if level == "junior":
        return ["junior", "entry level", "entry-level", "new grad", "graduate", "intern"]

    elif level == "mid":
        return ["mid", "mid level", "mid-level", "intermediate"]

    elif level == "senior":
        return ["senior", "sr.", "lead"]

    return []

def career_level_match(user_level, job_title):
    title = job_title.lower()
    level = user_level.lower()

    senior_words = [
        "senior",
        "sr.",
        "lead",
        "staff",
        "principal",
        "manager",
        "head",
        "director"
    ]

    junior_words = [
        "junior",
        "entry level",
        "entry-level",
        "new grad",
        "graduate",
        "intern"
    ]

    if level == "junior":
        for word in senior_words:
            if word in title:
                return False

    elif level == "mid":
        for word in ["senior", "staff", "principal", "director", "head"]:
            if word in title:
                return False

        for word in ["intern", "new grad"]:
            if word in title:
                return False

    elif level == "senior":
        for word in ["intern", "new grad", "entry level", "entry-level", "junior"]:
            if word in title:
                return False

    return True

def remote_location_match(user_location, job):
    user_location = (
        user_location or ''
    ).lower().strip()

    job_location = (
        job.get('location', '') or ''
    ).lower().strip()

    job_country = (
        job.get('country', '') or ''
    ).lower().strip()

    description = (
        job.get('description', '') or ''
    ).lower()

    job_text = (
        f"{job_location} "
        f"{job_country} "
        f"{description}"
    )

    country_aliases = {
        'palestine': [
            'palestine',
            'palestinian territories',
            'west bank'
        ],
        'jordan': [
            'jordan'
        ],
        'usa': [
            'united states',
            'usa',
            'u.s.',
            'u.s.a.',
            'us'
        ],
        'uk': [
            'united kingdom',
            'uk',
            'u.k.'
        ],
        'canada': [
            'canada'
        ],
        'germany': [
            'germany'
        ],
        'uae': [
            'united arab emirates',
            'uae',
            'u.a.e.'
        ],
        'saudi': [
            'saudi arabia'
        ],
        'qatar': [
            'qatar'
        ],
        'kuwait': [
            'kuwait'
        ],
        'egypt': [
            'egypt'
        ],
    }

    user_country = None

    for country, aliases in country_aliases.items():
        for alias in aliases:
            if alias in user_location:
                user_country = country
                break

        if user_country:
            break

    worldwide_phrases = [
        'remote worldwide',
        'worldwide remote',
        'work from anywhere',
        'work from any country',
        'anywhere in the world',
        'global remote',
        'location: worldwide'
    ]

    for phrase in worldwide_phrases:
        if phrase in job_text:
            return True

    # Detect country from both job country and job location
    job_country_name = None

    location_text = (
        f"{job_country} {job_location}"
    )

    for country, aliases in country_aliases.items():
        for alias in aliases:
            if alias in location_text:
                job_country_name = country
                break

        if job_country_name:
            break

    # Reject a remote job tied to another country
    if (
        job_country_name
        and user_country
        and job_country_name != user_country
    ):
        return False

    # Explicit country restrictions
    for country, aliases in country_aliases.items():
        for alias in aliases:
            restricted_phrases = [
                f'{alias} only',
                f'only in {alias}',
                f'must reside in {alias}',
                f'must live in {alias}',
                f'must be located in {alias}',
                f'located in {alias} only',
                f'residents of {alias} only',
                f'authorized to work in {alias}',
                f'work authorization in {alias}',
                f'eligible to work in {alias}',
            ]

            for phrase in restricted_phrases:
                if phrase in job_text:
                    if user_country != country:
                        return False

    europe_restrictions = [
        'eu only',
        'europe only',
        'european union only',
        'must reside in the eu',
        'must reside in europe',
        'must be located in europe',
        'remote within europe'
    ]

    european_locations = [
        'germany',
        'france',
        'spain',
        'italy',
        'netherlands',
        'belgium',
        'austria',
        'sweden',
        'denmark',
        'finland',
        'ireland',
        'portugal',
        'poland',
        'greece',
        'czech',
        'romania',
        'croatia'
    ]

    for phrase in europe_restrictions:
        if phrase in job_text:
            if not any(
                location in user_location
                for location in european_locations
            ):
                return False

    return True

# Read the text from an uploaded PDF file
def read_pdf(file):
    try:
        reader = PdfReader(file)
        return '\n'.join(page.extract_text() or '' for page in reader.pages).strip()
    except Exception:
        return ''


# AI feedback on a CV or cover letter for a specific job
def review_document(doc_type, text, job, profile):
    name = 'CV' if doc_type == 'cv' else 'cover letter'
    prompt = f"""
You are a career coach. Review this candidate's {name} for the job below.

Job title: {job['title']}
Company: {job['company']}
Job description:
{job['description'][:3000]}

Candidate level: {profile.career_level if profile else 'not given'}

The {name}:
{text[:6000]}

Answer in English with these sections, short bullet points, no markdown symbols like ** or #:
Strengths:
Missing for this job:
How to improve:
"""
    return ask_ai(prompt)


# AI interview questions for a specific job
def interview_questions(job, profile, skills):
    prompt = f"""
You are an interviewer for this job.

Job title: {job['title']}
Company: {job['company']}
Job description:
{job['description'][:3000]}

Candidate level: {profile.career_level if profile else 'not given'}
Candidate skills: {', '.join(skills) if skills else 'not given'}

Write 8 interview questions for this candidate: 3 technical, 3 behavioral, 2 about the company or role.
For each question add one short tip on how to answer.
Answer in English, numbered list, no markdown symbols like ** or #.
"""
    return ask_ai(prompt)