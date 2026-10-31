from django.db import models
from django.db.models import Q
from . import ai
import re
import bcrypt

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
ALLOWED_STATUSES = ['applied', 'interview', 'accepted', 'rejected']
MAX_FILE_SIZE = 5 * 1024 * 1024   # 5 MB


# ---------- Validation managers ----------

class UserManager(models.Manager):
    def reg_validation(self, formdata):
        errors = {}
        if len(formdata['first_name']) < 2:
            errors['first_name'] = 'First name must be at least 2 characters'
        if len(formdata['last_name']) < 2:
            errors['last_name'] = 'Last name must be at least 2 characters'
        if not EMAIL_REGEX.match(formdata['email']):
            errors['email'] = 'Invalid email address'
        elif User.objects.filter(email=formdata['email']).exists():
            errors['email'] = 'Email already registered'
        if len(formdata['password']) < 8:
            errors['password'] = 'Password must be at least 8 characters'
        if formdata['password'] != formdata['confirm_password']:
            errors['confirm_password'] = 'Passwords do not match'
        return errors

    def login_validation(self, formdata):
        errors = {}
        user = User.objects.filter(email=formdata['email']).first()
        if not user:
            errors['email'] = 'Email not found'
        elif not bcrypt.checkpw(formdata['password'].encode(), user.password.encode()):
            errors['password'] = 'Wrong password'
        elif user.status != 'active':
            errors['email'] = 'This account is inactive'
        return errors


class ProfileManager(models.Manager):
    def profile_validation(self, formdata):
        errors = {}
        if len(formdata['target_role']) < 2:
            errors['target_role'] = 'Please enter your target role'
        if not formdata.get('career_level'):
            errors['career_level'] = 'Please select your career level'
        if not str(formdata.get('years_experience', '')).isdigit():
            errors['years_experience'] = 'Years of experience must be a number'
        if len(formdata['preferred_location']) < 2:
            errors['preferred_location'] = 'Please enter your preferred location'
        if not formdata.getlist('work_mode'):
            errors['work_mode'] = 'Please select at least one work mode'
        if not formdata.getlist('employment_type'):
            errors['employment_type'] = 'Please select at least one employment type'
        return errors


class ContactMessageManager(models.Manager):
    def contact_validation(self, formdata):
        errors = {}
        if len(formdata['name']) < 2:
            errors['name'] = 'Name must be at least 2 characters'
        if not EMAIL_REGEX.match(formdata['email']):
            errors['email'] = 'Invalid email address'
        if len(formdata['subject']) < 3:
            errors['subject'] = 'Subject must be at least 3 characters'
        if len(formdata['message']) < 10:
            errors['message'] = 'Message must be at least 10 characters'
        return errors


# ---------- Models ----------

class User(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(max_length=254, unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=10, default='user')   # user or admin
    status = models.CharField(max_length=10, default='active')   # active or inactive
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = UserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    target_role = models.CharField(max_length=100)
    career_level = models.CharField(max_length=30)
    years_experience = models.PositiveIntegerField(default=0)
    preferred_location = models.CharField(max_length=100)
    work_mode = models.CharField(max_length=100)
    employment_type = models.CharField(max_length=100)
    bio = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = ProfileManager()

    def __str__(self):
        return f"{self.user} - {self.target_role}"

    # Turn the saved text (e.g. "remote,hybrid") into a list for the templates
    def work_mode_list(self):
        return self.work_mode.split(',') if self.work_mode else []

    def employment_type_list(self):
        return self.employment_type.split(',') if self.employment_type else []


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class UserSkill(models.Model):   # Many to Many Relation
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='user_skills')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'skill')   # Skill can't be repeated

    def __str__(self):
        return f"{self.user} - {self.skill}"


class Application(models.Model):   # One to Many Relation
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    job_title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=150, null=True, blank=True)
    job_url = models.URLField(max_length=500)
    job_description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=10, default='applied')   # applied / interview / accepted / rejected
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'job_url')   # Can't apply to the same job more than one time

    def __str__(self):
        return f"{self.job_title} - {self.company}"


class Favorite(models.Model):   # One to Many Relation
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    job_title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=150, null=True, blank=True)
    job_url = models.URLField(max_length=500)
    job_description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'job_url')   # Can't save the same job twice

    def __str__(self):
        return f"{self.job_title} - {self.company}"


class SearchHistory(models.Model):   # One to Many Relation
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='searches')
    query = models.CharField(max_length=255)
    results_count = models.PositiveIntegerField(default=0)
    results = models.JSONField(default=list)   # The jobs found in this search
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.query}"


class ContactMessage(models.Model):   # No user field: any visitor can send a message without an account
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = ContactMessageManager()

    def __str__(self):
        return f"{self.name} - {self.subject}"


class AIReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_reviews')
    application = models.ForeignKey(Application, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_reviews')
    review_type = models.CharField(max_length=15)
    job_url = models.URLField(max_length=500, null=True, blank=True)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    uploaded_file = models.FileField(upload_to='ai_documents/', null=True, blank=True)
    content = models.TextField()
    result = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.review_type}"


# ---------- Users ----------

def create_user(data):
    password = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()).decode()
    return User.objects.create(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        password=password
    )


def get_user_by_email(email):
    return User.objects.filter(email=email).first()


def get_user_by_id(user_id):
    # Returns None instead of error 500 when the user does not exist
    return User.objects.filter(id=user_id).first()


def search_users(search):
    users = User.objects.all().order_by('-created_at')
    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    return users


def switch_user_status(user):
    user.status = 'inactive' if user.status == 'active' else 'active'
    user.save()


def admin_stats():
    return {
        'total_users': User.objects.count(),
        'total_applications': Application.objects.count(),
        'total_messages': ContactMessage.objects.count(),
        'contact_messages': ContactMessage.objects.all().order_by('-created_at'),
    }


# ---------- Profile and skills ----------

def get_profile_by_user(user_id):
    return Profile.objects.filter(user_id=user_id).first()


def create_profile(user, data):
    return Profile.objects.create(
        user=user,
        target_role=data['target_role'],
        career_level=data['career_level'],
        years_experience=data['years_experience'],
        preferred_location=data['preferred_location'],
        work_mode=','.join(data.getlist('work_mode')),
        employment_type=','.join(data.getlist('employment_type')),
        bio=data['bio']
    )


def update_profile(profile, data):
    profile.target_role = data['target_role']
    profile.career_level = data['career_level']
    profile.years_experience = data['years_experience']
    profile.preferred_location = data['preferred_location']
    profile.work_mode = ','.join(data.getlist('work_mode'))
    profile.employment_type = ','.join(data.getlist('employment_type'))
    profile.bio = data['bio']
    profile.save()
    return profile


def get_user_skills(user_id):
    return UserSkill.objects.filter(user_id=user_id).select_related('skill')


def get_skill_names(user):
    return [user_skill.skill.name for user_skill in get_user_skills(user.id)]


def add_user_skill(user, skill_name):
    skill, created = Skill.objects.get_or_create(name=skill_name)
    UserSkill.objects.get_or_create(user=user, skill=skill)
    return skill


def remove_user_skill(user_id, skill_id):
    # Remove only the link between the user and the skill
    UserSkill.objects.filter(user_id=user_id, skill_id=skill_id).delete()


# ---------- Jobs ----------

def find_job(jobs, job_id):
    # Find one job inside the search results saved in the session
    return next((job for job in jobs if job.get('job_id') == job_id), None)


def saved_job_dict(item, reason):
    # Turn a saved Application or Favorite into the same job shape used by the templates
    return {
        'title': item.job_title,
        'company': item.company,
        'location': item.location or '',
        'description': item.job_description or '',
        'apply_link': item.job_url,
        'match': 'Possible',
        'reason': reason,
        'job_id': '',
    }


def find_matched_jobs(user, profile):
    # Search jobs, match them with the profile and save the search in the history
    if profile.work_mode_list() == ['remote']:
        query = f"{profile.target_role} remote worldwide"
        jobs = ai.search_jobs(query, country='us', num=15, remote=True)
    else:
        query = f"{profile.target_role} in {profile.preferred_location}"
        country = ai.get_country_code(profile.preferred_location)
        jobs = ai.search_jobs(query, country=country, num=15, remote=False)

    if not jobs:
        return {'success': False, 'message': 'No jobs found. Please try again.'}

    matched_jobs = ai.match_jobs(profile, get_skill_names(user), jobs)
    if not matched_jobs:
        return {'success': False, 'message': 'Could not find suitable matches. Please try again.'}

    SearchHistory.objects.create(user=user, query=query, results_count=len(matched_jobs), results=matched_jobs)
    return {'success': True, 'jobs': matched_jobs}


# ---------- Applications ----------

def get_user_applications(user_id):
    return Application.objects.filter(user_id=user_id).order_by('-created_at')


def get_user_application(user, application_id):
    return Application.objects.filter(id=application_id, user=user).first()


def get_application_by_url(user, job_url):
    return Application.objects.filter(user=user, job_url=job_url).first()


def has_applied(user_id, job_url):
    return Application.objects.filter(user_id=user_id, job_url=job_url).exists()


def apply_job(user, job):
    # Save the job only when the user applies
    if has_applied(user.id, job['apply_link']):
        return False
    Application.objects.create(
        user=user,
        job_title=job['title'],
        company=job['company'] or 'Unknown company',
        location=job['location'],
        job_url=job['apply_link'],
        job_description=job['description'][:2000],
    )
    return True


def remove_application(user, application_id):
    # delete() returns (number of deleted rows, details)
    return Application.objects.filter(id=application_id, user=user).delete()[0] > 0


def update_application_status(application, status):
    if status in ALLOWED_STATUSES:
        application.status = status
        application.save()


# ---------- Favorites ----------

def get_user_favorites(user_id):
    return Favorite.objects.filter(user_id=user_id).order_by('-created_at')


def get_user_favorite(user, favorite_id):
    return Favorite.objects.filter(id=favorite_id, user=user).first()


def is_favorite(user_id, job_url):
    return Favorite.objects.filter(user_id=user_id, job_url=job_url).exists()


def toggle_favorite(user, job):
    # Save the job, or remove it if it is already saved
    favorite = Favorite.objects.filter(user=user, job_url=job['apply_link']).first()
    if favorite:
        favorite.delete()
        return False
    Favorite.objects.create(
        user=user,
        job_title=job['title'],
        company=job['company'] or 'Unknown company',
        location=job['location'],
        job_url=job['apply_link'],
        job_description=job['description'][:2000],
    )
    return True


def remove_favorite(user, favorite_id):
    Favorite.objects.filter(id=favorite_id, user=user).delete()


# ---------- Search history ----------

def get_search_history(user):
    return SearchHistory.objects.filter(user=user).order_by('-created_at')


def get_user_search(user, search_id):
    return SearchHistory.objects.filter(id=search_id, user=user).first()


def clear_search_history(user):
    SearchHistory.objects.filter(user=user).delete()


# ---------- Contact messages ----------

def create_contact_message(data):
    return ContactMessage.objects.create(
        name=data['name'],
        email=data['email'],
        subject=data['subject'],
        message=data['message'],
    )


def get_contact_message(message_id):
    return ContactMessage.objects.filter(id=message_id).first()


def remove_contact_message(message_id):
    return ContactMessage.objects.filter(id=message_id).delete()[0] > 0


# ---------- AI tools ----------

def get_ai_reviews(user, job_url):
    # Latest saved AI result of each tool for this job
    reviews = {}
    for key, review_type in [('cv_review', 'cv'), ('cover_review', 'cover_letter'), ('interview_review', 'interview')]:
        reviews[key] = AIReview.objects.filter(
            user=user, job_url=job_url, review_type=review_type
        ).order_by('-created_at').first()
    return reviews


def get_user_review(user, review_id):
    return AIReview.objects.filter(id=review_id, user=user).first()


def get_ai_job(user, jobs, job_id, job_url):
    # Find the job in the session first, then in My Applications
    job = find_job(jobs, job_id)
    if job:
        job_url = job.get('apply_link', job_url)
    application = get_application_by_url(user, job_url) if job_url else None
    if not job and application:
        job = saved_job_dict(application, '')
    return job, application


def read_uploaded_pdf(file):
    # Returns (text, error)
    if not file.name.lower().endswith('.pdf'):
        return '', 'Only PDF files are allowed'
    if file.size > MAX_FILE_SIZE:
        return '', 'File must be smaller than 5 MB'
    content = ai.read_pdf(file)
    if len(content) < 50:
        return '', 'Could not read text from this PDF'
    file.seek(0)   # Go back to the start so the file can be saved
    return content, ''


def run_ai_tool(user, job, application, tool, file, text_content):
    # Run one AI tool, save the result and return the JSON data
    profile = get_profile_by_user(user.id)
    used_file = None

    if tool == 'cv':
        if not file:
            return {'success': False, 'message': 'Please upload your CV as a PDF'}
        content, error = read_uploaded_pdf(file)
        if error:
            return {'success': False, 'message': error}
        used_file = file
        result = ai.review_document('cv', content, job, profile)

    elif tool == 'cover_letter':
        if text_content:
            content = text_content
        elif file:
            content, error = read_uploaded_pdf(file)
            if error:
                return {'success': False, 'message': error}
            used_file = file
        else:
            return {'success': False, 'message': 'Please upload a PDF or write your cover letter'}
        if len(content) < 30:
            return {'success': False, 'message': 'Cover letter text is too short'}
        result = ai.review_document('cover_letter', content, job, profile)

    elif tool == 'interview':
        content = f"{job['title']} - {job['company']}"
        result = ai.interview_questions(job, profile, get_skill_names(user))

    else:
        return {'success': False, 'message': 'Unknown tool'}

    if not result:
        return {'success': False, 'message': 'AI is busy, please try again'}

    file_name = used_file.name if used_file else ''
    AIReview.objects.create(
        user=user,
        application=application,
        review_type=tool,
        job_url=job.get('apply_link', ''),
        file_name=file_name,
        uploaded_file=used_file,
        content=content,
        result=result,
    )
    return {'success': True, 'result': result, 'file_name': file_name}
