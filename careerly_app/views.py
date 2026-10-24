from django.shortcuts import render, redirect
from django.contrib import messages
from . import models
from django.db.models import Q
from django.http import JsonResponse
from . import ai
from urllib.parse import quote


def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')    

def register(request):
    if request.method == 'POST':
        errors = models.User.objects.reg_validation(request.POST)
        if errors:
            request.session['first_name'] = request.POST['first_name']
            request.session['last_name'] = request.POST['last_name']
            request.session['email'] = request.POST['email']

            for value in errors.values():
                messages.error(request, value)
            return redirect('/register')

        user = models.create_user(request.POST)
        request.session['user_id'] = user.id
        for key in ['first_name', 'last_name', 'email']:
            if key in request.session:
                del request.session[key]
        return redirect('/profile')
    return render(request, 'register.html')

def login(request):
    if request.method == 'POST':
        errors = models.User.objects.login_validation(request.POST)
        if errors:
            request.session['login_email'] = request.POST['email']

            for value in errors.values():
                messages.error(request, value)
            return redirect('/login')
        
        user = models.get_user_by_email(request.POST['email'])
        request.session['user_id'] = user.id

        if 'login_email' in request.session:
            del request.session['login_email']

        if user.role == 'admin':
            return redirect('/admin-dashboard')
        return redirect('/dashboard')
    
    return render(request, 'login.html')

def contact(request):
    if request.method == 'POST':
        errors = models.ContactMessage.objects.contact_validation(request.POST)
        if errors:
            for value in errors.values():
                messages.error(request, value)
            # Save input so the user does not retype it
            request.session['contact_name'] = request.POST['name']
            request.session['contact_email'] = request.POST['email']
            request.session['contact_subject'] = request.POST['subject']
            request.session['contact_message'] = request.POST['message']
            return redirect('/contact')

        models.ContactMessage.objects.create(
            name=request.POST['name'],
            email=request.POST['email'],
            subject=request.POST['subject'],
            message=request.POST['message'],
        )
        # Clear saved input after success
        for key in ['contact_name', 'contact_email', 'contact_subject', 'contact_message']:
            request.session.pop(key, None)
        messages.success(request, 'Your message has been sent successfully!')
        return redirect('/contact')

    return render(request, 'contact.html')


def admin_dashboard(request):
    if 'user_id' not in request.session:
        return redirect('/login')

    admin = models.User.objects.get(id=request.session['user_id'])
    # Normal users cannot access this page
    if admin.role != 'admin':
        return redirect('/dashboard')

    # Search by name or email
    search = request.GET.get('search', '')
    users = models.User.objects.all().order_by('-created_at')
    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )

    context = {
        'admin': admin,
        'users': users,
        'search': search,
        'total_users': models.User.objects.count(),
        'total_applications': models.Application.objects.count(),
        'total_messages': models.ContactMessage.objects.count(),
        'contact_messages': models.ContactMessage.objects.all().order_by('-created_at'),
    }
    return render(request, 'admin_dashboard.html', context)

#admin user
def admin_user(request, id):
    if 'user_id' not in request.session:
        return redirect('/login')
    admin = models.User.objects.get(id=request.session['user_id'])
    if admin.role != 'admin':
        return redirect('/dashboard')

    context = {
        'admin': admin,
        'user': models.User.objects.get(id=id),
    }
    return render(request, 'admin_user.html', context)


# activate-deactivate the user
def toggle_user_status(request, id):
    if 'user_id' not in request.session:
        return redirect('/login')
    admin = models.User.objects.get(id=request.session['user_id'])
    if admin.role != 'admin' or request.method != 'POST':
        return redirect('/dashboard')

    user = models.User.objects.get(id=id)
    # admin can't activate his self
    if user.id == admin.id:
        messages.error(request, 'You cannot deactivate your own account')
    elif user.status == 'active':
        user.status = 'inactive'
        user.save()
        messages.success(request, 'Account deactivated')
    else:
        user.status = 'active'
        user.save()
        messages.success(request, 'Account activated')
    return redirect(f'/admin-dashboard/user/{id}')    


def admin_message(request, id):
    if 'user_id' not in request.session:
        return redirect('/login')
    admin = models.User.objects.get(id=request.session['user_id'])
    if admin.role != 'admin':
        return redirect('/dashboard')

    context = {
        'admin': admin,
        'msg': models.ContactMessage.objects.get(id=id),
    }
    return render(request, 'admin_message.html', context)


def logout(request):
    request.session.flush()
    return redirect('/')

def profile(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('/login')

    user = models.get_user_by_id(request.session['user_id'])
    # Admin has no profile page
    if user.role == 'admin':
        return redirect('/admin-dashboard')
    profile = models.get_profile_by_user(user.id)
    skills = models.get_user_skills(user.id)
    edit_mode = request.GET.get('edit') == 'true'

    context = {
        'user': user,
        'profile': profile,
        'skills': skills,
        'edit_mode': edit_mode
    }

    return render(request, 'profile.html', context)


def create_profile(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('/login')

    user = models.get_user_by_id(request.session['user_id'])

    # Prevent creating more than one profile
    if models.get_profile_by_user(user.id):
        return redirect('/profile')

    if request.method == 'POST':
        errors = models.Profile.objects.profile_validation(request.POST)

        if errors:
            for value in errors.values():
                messages.error(request, value)
            return redirect('/profile')

        models.create_profile(user, request.POST)
        return redirect('/profile')

    return redirect('/profile')


def edit_profile(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('/login')

    user = models.get_user_by_id(request.session['user_id'])
    profile = models.get_profile_by_user(user.id)

    if not profile:
        return redirect('/profile')

    if request.method == 'POST':
        errors = models.Profile.objects.profile_validation(request.POST)

        if errors:
            for value in errors.values():
                messages.error(request, value)
            return redirect('/profile?edit=true')

        models.update_profile(profile, request.POST)
        return redirect('/profile')

    return redirect('/profile?edit=true')


def add_skill(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return JsonResponse({'success': False, 'message': 'Please log in first'}, status=401)

    if request.method == 'POST':
        skill_name = request.POST.get('skill', '').strip()

        if not skill_name:
            return JsonResponse({'success': False, 'message': 'Skill is required'})

        user = models.get_user_by_id(request.session['user_id'])
        skill = models.add_user_skill(user, skill_name)

        return JsonResponse({
            'success': True,
            'skill_id': skill.id,
            'skill_name': skill.name
        })

    return JsonResponse({'success': False}, status=400)


def remove_skill(request, skill_id):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return JsonResponse({'success': False}, status=401)

    if request.method == 'POST':
        models.remove_user_skill(request.session['user_id'], skill_id)

        return JsonResponse({'success': True})

    return JsonResponse({'success': False}, status=400)

def job_details(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('/login')

    user = models.get_user_by_id(request.session['user_id'])
    if user.role == 'admin':
        return redirect('/admin-dashboard')

    # Jobs are saved in the session by Find My Best Jobs
    job_id = request.GET.get('id', '')
    jobs = request.session.get('jobs', [])
    job = next((j for j in jobs if j['job_id'] == job_id), None)


    if not job:
        messages.error(request, 'Job not found, please search again')
        return redirect('/dashboard')

    context = {
        'user': user,
        'job': job,
        'applied': models.has_applied(user.id, job['apply_link']),
        'favorite': models.is_favorite(user.id, job['apply_link']),
    }
    return render(request, 'job_details.html', context)


def job_ai(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return JsonResponse({'success': False, 'message': 'Please log in first'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'success': False}, status=400)

    user = models.get_user_by_id(request.session['user_id'])
    tool = request.POST.get('tool', '')
    job_id = request.POST.get('job_id', '')

    # Find the job saved in the session
    jobs = request.session.get('jobs', [])
    job = next((j for j in jobs if j['job_id'] == job_id), None)
    if not job:
        return JsonResponse({'success': False, 'message': 'Job not found, please search again'})

    profile = models.get_profile_by_user(user.id)

    if tool in ['cv', 'cover_letter']:
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'success': False, 'message': 'Please upload a PDF file'})
        if not file.name.lower().endswith('.pdf'):
            return JsonResponse({'success': False, 'message': 'Only PDF files are allowed'})
        if file.size > 5 * 1024 * 1024:
            return JsonResponse({'success': False, 'message': 'File must be smaller than 5 MB'})

        content = ai.read_pdf(file)
        if len(content) < 50:
            return JsonResponse({'success': False, 'message': 'Could not read text from this PDF'})
        result = ai.review_document(tool, content, job, profile)

    elif tool == 'interview':
        skills = [us.skill.name for us in models.get_user_skills(user.id)]
        content = f"{job['title']} - {job['company']}"
        result = ai.interview_questions(job, profile, skills)

    else:
        return JsonResponse({'success': False, 'message': 'Unknown tool'})

    if not result:
        return JsonResponse({'success': False, 'message': 'AI is busy, please try again'})

    # Save the result in AIReview
    models.AIReview.objects.create(
        user=user,
        review_type=tool,
        content=content,
        result=result,
    )
    return JsonResponse({'success': True, 'result': result})


def dashboard(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('/login')

    user = models.get_user_by_id(request.session['user_id'])

    # Prevent admin from accessing user dashboard
    if user.role != 'user':
        return redirect('/admin-dashboard')

    profile = models.get_profile_by_user(user.id)

    # User must complete profile first
    if not profile:
        return redirect('/profile')

    skills = models.get_user_skills(user.id)
    applications = models.get_user_applications(user.id)

    context = {
        'user': user,
        'profile': profile,
        'skills': skills,
        'applications': applications,
        'saved_jobs': request.session.get('jobs', []),
        'favorites': models.get_user_favorites(user.id),
    }

    return render(request, 'dashboard.html', context)


def find_jobs(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return JsonResponse({'success': False, 'message': 'Please log in first'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'success': False}, status=400)

    user = models.get_user_by_id(request.session['user_id'])

    if user.role != 'user':
        return JsonResponse({'success': False}, status=403)

    profile = models.get_profile_by_user(user.id)

    if not profile:
        return JsonResponse({
            'success': False,
            'message': 'Please complete your profile first'
        })

    skills = [
        user_skill.skill.name
        for user_skill in models.get_user_skills(user.id)
    ]

    country = ai.get_country_code(profile.preferred_location)

    if profile.work_mode_list() == ['remote']:

        query = f"{profile.target_role} remote worldwide"

        jobs = ai.search_jobs(query,country='us',num=15,remote=True)

    else:

        query = f"{profile.target_role} in {profile.preferred_location}"

        jobs = ai.search_jobs(
        query,country=country,num=15,remote=False)

    if not jobs:
        return JsonResponse({
            'success': False,
            'message': 'No jobs found. Please try again.'
        })

    matched_jobs = ai.match_jobs(
        profile,
        skills,
        jobs
    )

    if not matched_jobs:
        return JsonResponse({
            'success': False,
            'message': 'Could not find suitable matches. Please try again.'
        })

    # Save jobs in session for Job Details page
    request.session['jobs'] = matched_jobs

    return JsonResponse({
        'success': True,
        'jobs': matched_jobs
    })

def apply_job(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('/login')

    if request.method != 'POST':
        return redirect('/dashboard')

    user = models.get_user_by_id(request.session['user_id'])
    job_id = request.POST.get('job_id', '')
    jobs = request.session.get('jobs', [])
    job = next((j for j in jobs if j['job_id'] == job_id), None)

    if not job or not job['apply_link']:
        messages.error(request, 'Job not found, please search again')
        return redirect('/dashboard')

    # Can't apply to the same job more than one time
    if models.has_applied(user.id, job['apply_link']):
        messages.error(request, 'You already applied to this job')
        return redirect('/dashboard')

    models.create_application(user, job)
    messages.success(request, 'Job added to My Applications')
    return redirect('/dashboard')    

def application_details(request, id):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('/login')

    user = models.get_user_by_id(request.session['user_id'])

    if user.role != 'user':
        return redirect('/admin-dashboard')

    application = models.Application.objects.filter(
        id=id,
        user=user
    ).first()

    if not application:
        messages.error(request, 'Application not found')
        return redirect('/dashboard')

    job = {
        'title': application.job_title,
        'company': application.company,
        'location': application.location,
        'description': application.job_description,
        'apply_link': application.job_url,
        'match': 'Possible',
        'reason': 'This job was saved in your applications.',
        'job_id': ''
    }

    context = {
        'user': user,
        'job': job,
        'applied': True,
    }

    return render(request, 'job_details.html', context)

def favorite_job(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('/login')

    if request.method != 'POST':
        return redirect('/dashboard')

    user = models.get_user_by_id(request.session['user_id'])
    job_id = request.POST.get('job_id', '')
    jobs = request.session.get('jobs', [])
    job = next((j for j in jobs if j['job_id'] == job_id), None)

    if not job or not job['apply_link']:
        messages.error(request, 'Job not found, please search again')
        return redirect('/dashboard')
    models.toggle_favorite(user, job)
    return redirect(f'/job?id={quote(job_id)}')

def favorite_details(request, id):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('/login')

    user = models.get_user_by_id(request.session['user_id'])
    favorite = models.Favorite.objects.filter(id=id, user=user).first()

    if not favorite:
        messages.error(request, 'Job not found')
        return redirect('/dashboard')

    job = {
        'title': favorite.job_title,
        'company': favorite.company,
        'location': favorite.location,
        'description': favorite.job_description,
        'apply_link': favorite.job_url,
        'match': 'Possible',
        'reason': 'This job was saved in your favourites.',
        'job_id': ''
    }

    context = {
        'user': user,
        'job': job,
        'applied': models.has_applied(user.id, favorite.job_url),
        'favorite_id': favorite.id,
    }
    return render(request, 'job_details.html', context)    

def remove_favorite(request, id):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('/login')

    if request.method == 'POST':
        models.Favorite.objects.filter(id=id, user_id=request.session['user_id']).delete()
    return redirect('/dashboard')    