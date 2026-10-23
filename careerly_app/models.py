from django.db import models
import re
import bcrypt

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')


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
        if not formdata.get('work_mode'):
            errors['work_mode'] = 'Please select your preferred work mode'
        if not formdata.get('employment_type'):
            errors['employment_type'] = 'Please select your employment type'
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
    work_mode = models.CharField(max_length=20)
    employment_type = models.CharField(max_length=30)
    bio = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = ProfileManager()

    def __str__(self):
        return f"{self.user} - {self.target_role}"



class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class UserSkill(models.Model): # Many to Many Relation
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='user_skills')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'skill')   # Skill Can't be repeated

    def __str__(self):
        return f"{self.user} - {self.skill}"



class Application(models.Model): # One to Many Relation 
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



class ContactMessage(models.Model): # No user field : because any visitor can send message without having account
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_reviews') # One to Many between AI and user
    application = models.ForeignKey(Application, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_reviews') # Many to Many
    review_type = models.CharField(max_length=15)   # cv / cover_letter / interview
    content = models.TextField()  # CV or Cover Letter
    result = models.TextField()   # AI Response ( Notes / AI Interview question)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.review_type}"


def create_user(data):
    password = bcrypt.hashpw(data['password'].encode(),bcrypt.gensalt()).decode()
    return User.objects.create(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        password=password
    )

def get_user_by_email(email):
    return User.objects.filter(email=email).first()

# Get user by id
def get_user_by_id(user_id):
    return User.objects.get(id=user_id)

# Get profile for a specific user
def get_profile_by_user(user_id):
    return Profile.objects.filter(user_id=user_id).first()

# Create a new profile
def create_profile(user, data):
    return Profile.objects.create(
        user=user,
        target_role=data['target_role'],
        career_level=data['career_level'],
        years_experience=data['years_experience'],
        preferred_location=data['preferred_location'],
        work_mode=data['work_mode'],
        employment_type=data['employment_type'],
        bio=data['bio']
    )


# Update an existing profile
def update_profile(profile, data):
    profile.target_role = data['target_role']
    profile.career_level = data['career_level']
    profile.years_experience = data['years_experience']
    profile.preferred_location = data['preferred_location']
    profile.work_mode = data['work_mode']
    profile.employment_type = data['employment_type']
    profile.bio = data['bio']
    profile.save()

    return profile

# Get all skills for a user
def get_user_skills(user_id):
    return UserSkill.objects.filter(user_id=user_id).select_related('skill')

# Add a skill to a user
def add_user_skill(user, skill_name):
    skill, created = Skill.objects.get_or_create(name=skill_name)
    UserSkill.objects.get_or_create(user=user, skill=skill)

    return skill

# Remove a skill from a user
def remove_user_skill(user_id, skill_id):
    UserSkill.objects.filter(user_id=user_id, skill_id=skill_id).delete()


# Get all applications for a user
def get_user_applications(user_id):
    return Application.objects.filter(user_id=user_id).order_by('-created_at')

def create_application(user, job):
    # Save the job only when the user applies
    return Application.objects.create(
        user=user,
        job_title=job['title'],
        company=job['company'] or 'Unknown company',
        location=job['location'],
        job_url=job['apply_link'],
        job_description=job['description'][:2000],
    )


def has_applied(user_id, job_url):
    return Application.objects.filter(user_id=user_id, job_url=job_url).exists()    