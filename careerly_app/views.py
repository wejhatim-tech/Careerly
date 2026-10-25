from django.shortcuts import render, redirect
from django.contrib import messages
from . import models
from django.db.models import Q
from django.http import JsonResponse, FileResponse
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

def remove_admin_message(request, id):
    if 'user_id' not in request.session:
        return redirect('/login')

    admin = models.User.objects.get(id=request.session['user_id'])

    if admin.role != 'admin':
        return redirect('/dashboard')

    if request.method == 'POST':
        message = models.ContactMessage.objects.filter(id=id).first()

        if message:
            message.delete()
            messages.success(request, 'Message removed successfully')

    return redirect('/admin-dashboard')

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

    job_id = request.GET.get('id', '')
    jobs = request.session.get('jobs', [])

    job = next(
        (
            job_item
            for job_item in jobs
            if job_item.get('job_id') == job_id
        ),
        None
    )

    if not job:
        messages.error(
            request,
            'Job not found, please search again'
        )
        return redirect('/dashboard')

    job_url = job.get('apply_link', '')

    # Get latest saved AI results for this job
    cv_review = models.AIReview.objects.filter(
        user=user,
        job_url=job_url,
        review_type='cv'
    ).order_by('-created_at').first()

    cover_review = models.AIReview.objects.filter(
        user=user,
        job_url=job_url,
        review_type='cover_letter'
    ).order_by('-created_at').first()

    interview_review = models.AIReview.objects.filter(
        user=user,
        job_url=job_url,
        review_type='interview'
    ).order_by('-created_at').first()

    context = {
        'user': user,
        'job': job,
        'applied': models.has_applied(
            user.id,
            job_url
        ),
        'favorite': models.is_favorite(
            user.id,
            job_url
        ),
        'cv_review': cv_review,
        'cover_review': cover_review,
        'interview_review': interview_review,
    }

    return render(
        request,
        'job_details.html',
        context
    )


def job_ai(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return JsonResponse({
            'success': False,
            'message': 'Please log in first'
        }, status=401)

    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Invalid request'
        }, status=400)

    user = models.get_user_by_id(
        request.session['user_id']
    )

    if user.role != 'user':
        return JsonResponse({
            'success': False,
            'message': 'Access denied'
        }, status=403)

    tool = request.POST.get('tool', '')
    job_id = request.POST.get('job_id', '')
    job_url = request.POST.get('job_url', '')

    jobs = request.session.get('jobs', [])

    job = None

    # Try to find the job in the current search session
    if job_id:
        job = next(
            (
                job_item
                for job_item in jobs
                if job_item.get('job_id') == job_id
            ),
            None
        )

    application = None

    # If job was found in session, get its real URL
    if job:
        job_url = job.get(
            'apply_link',
            job_url
        )

    # If job is not in session, try My Applications
    if not job and job_url:
        application = models.Application.objects.filter(
            user=user,
            job_url=job_url
        ).first()

        if application:
            job = {
                'job_id': '',
                'title': application.job_title,
                'company': application.company,
                'location': application.location or '',
                'description': (
                    application.job_description or ''
                ),
                'apply_link': application.job_url,
            }

    # If job is not in My Applications, try Saved Jobs
    if not job and job_url:
        favorite = models.Favorite.objects.filter(
            user=user,
            job_url=job_url
        ).first()

        if favorite:
            job = {
                'job_id': '',
                'title': favorite.job_title,
                'company': favorite.company,
                'location': favorite.location or '',
                'description': (
                    favorite.job_description or ''
                ),
                'apply_link': favorite.job_url,
            }

    if not job:
        return JsonResponse({
            'success': False,
            'message': 'Job not found'
        })

    # Find related application if it exists
    if not application:
        application = models.Application.objects.filter(
            user=user,
            job_url=job.get('apply_link', '')
        ).first()

    profile = models.get_profile_by_user(
        user.id
    )

    content = ''
    result = ''
    file_name = ''
    uploaded_file = None

    # CV Feedback
    if tool == 'cv':
        file = request.FILES.get('file')

        if not file:
            return JsonResponse({
                'success': False,
                'message': (
                    'Please upload your CV as a PDF'
                )
            })

        if not file.name.lower().endswith('.pdf'):
            return JsonResponse({
                'success': False,
                'message': 'Only PDF files are allowed'
            })

        if file.size > 5 * 1024 * 1024:
            return JsonResponse({
                'success': False,
                'message': (
                    'File must be smaller than 5 MB'
                )
            })

        content = ai.read_pdf(file)

        if len(content) < 50:
            return JsonResponse({
                'success': False,
                'message': (
                    'Could not read text from this PDF'
                )
            })

        file_name = file.name
        file.seek(0)
        uploaded_file = file

        result = ai.review_document(
            'cv',
            content,
            job,
            profile
        )

    # Cover Letter Feedback
    elif tool == 'cover_letter':
        file = request.FILES.get('file')
        text_content = request.POST.get(
            'text_content',
            ''
        ).strip()

        # User wrote cover letter as text
        if text_content:
            content = text_content

        # User uploaded cover letter as PDF
        elif file:
            if not file.name.lower().endswith('.pdf'):
                return JsonResponse({
                    'success': False,
                    'message': (
                        'Only PDF files are allowed'
                    )
                })

            if file.size > 5 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'message': (
                        'File must be smaller than 5 MB'
                    )
                })

            content = ai.read_pdf(file)

            if len(content) < 50:
                return JsonResponse({
                    'success': False,
                    'message': (
                        'Could not read text from this PDF'
                    )
                })

            file_name = file.name
            file.seek(0)
            uploaded_file = file

        else:
            return JsonResponse({
                'success': False,
                'message': (
                    'Please upload a PDF or write '
                    'your cover letter'
                )
            })

        if len(content) < 30:
            return JsonResponse({
                'success': False,
                'message': (
                    'Cover letter text is too short'
                )
            })

        result = ai.review_document(
            'cover_letter',
            content,
            job,
            profile
        )

    # Interview Questions
    elif tool == 'interview':
        skills = [
            user_skill.skill.name
            for user_skill
            in models.get_user_skills(user.id)
        ]

        content = (
            f"{job['title']} - {job['company']}"
        )

        result = ai.interview_questions(
            job,
            profile,
            skills
        )

    else:
        return JsonResponse({
            'success': False,
            'message': 'Unknown tool'
        })

    if not result:
        return JsonResponse({
            'success': False,
            'message': (
                'AI is busy, please try again'
            )
        })

    models.AIReview.objects.create(
        user=user,
        application=application,
        review_type=tool,
        job_url=job.get('apply_link', ''),
        file_name=file_name,
        uploaded_file=uploaded_file,
        content=content,
        result=result,
    )

    return JsonResponse({
        'success': True,
        'result': result,
        'file_name': file_name,
    })

def download_ai_file(request, id):
    if 'user_id' not in request.session:
        return redirect('/login')

    review = models.AIReview.objects.filter(
        id=id,
        user_id=request.session['user_id']
    ).first()

    if not review or not review.uploaded_file:
        messages.error(request, 'File not found')
        return redirect('/dashboard')

    return FileResponse(
        review.uploaded_file.open('rb'),
        as_attachment=True,
        filename=review.file_name
    )

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
    }

    return render(request, 'dashboard.html', context)

def saved_jobs(request):
    if 'user_id' not in request.session:
        return redirect('/login')

    user = models.get_user_by_id(request.session['user_id'])

    if user.role != 'user':
        return redirect('/admin-dashboard')

    favorites = models.get_user_favorites(user.id)

    context = {
        'user': user,
        'favorites': favorites,
    }

    return render(request, 'saved_jobs.html', context)

def find_jobs(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return JsonResponse({
            'success': False,
            'message': 'Please log in first'
        }, status=401)

    if request.method != 'POST':
        return JsonResponse({
            'success': False
        }, status=400)

    user = models.get_user_by_id(
        request.session['user_id']
    )

    if user.role != 'user':
        return JsonResponse({
            'success': False
        }, status=403)

    profile = models.get_profile_by_user(
        user.id
    )

    if not profile:
        return JsonResponse({
            'success': False,
            'message': (
                'Please complete your profile first'
            )
        })

    skills = [
        user_skill.skill.name
        for user_skill
        in models.get_user_skills(user.id)
    ]

    work_modes = profile.work_mode_list()

    country = ai.get_country_code(
        profile.preferred_location
    )

    jobs = []

    # Search worldwide remote jobs
    if 'remote' in work_modes:
        remote_query = (
            f"{profile.target_role} remote worldwide"
        )

        remote_jobs = ai.search_jobs(
            remote_query,
            country=None,
            num=20,
            remote=True
        )

        # Keep only remote jobs suitable for the user's location
        remote_jobs = [
            job
            for job in remote_jobs
            if ai.remote_location_match(
                profile.preferred_location,
                job
            )
        ]

        jobs.extend(remote_jobs)

    # Search local jobs for hybrid or on-site
    if (
        'hybrid' in work_modes
        or 'onsite' in work_modes
    ):
        preferred_location = (
            profile.preferred_location.strip()
        )

        # Convert "Palestine Nablus"
        # to "Nablus, Palestine"
        if preferred_location.lower().startswith(
            'palestine '
        ):
            city = preferred_location[
                len('palestine '):
            ].strip()

            local_location = (
                f"{city}, Palestine"
            )

        else:
            local_location = preferred_location

        local_query = (
            f"{profile.target_role} "
            f"in {local_location}"
        )

        local_jobs = ai.search_jobs(
            local_query,
            country=country,
            num=20,
            remote=False
        )
        

        # On-site only: remove remote jobs
        if work_modes == ['onsite']:
            local_jobs = [
                job
                for job in local_jobs
                if not job.get('is_remote')
            ]

        jobs.extend(local_jobs)

    # Remove duplicate jobs
    unique_jobs = []
    seen_urls = set()

    for job in jobs:
        job_url = job.get('apply_link')

        if not job_url:
            continue

        if job_url in seen_urls:
            continue

        seen_urls.add(job_url)
        unique_jobs.append(job)

    jobs = unique_jobs

    if not jobs:
        return JsonResponse({
            'success': False,
            'message': (
                'No jobs found. Please try again.'
            )
        })

    matched_jobs = ai.match_jobs(
        profile,
        skills,
        jobs
    )

    if not matched_jobs:
        return JsonResponse({
            'success': False,
            'message': (
                'Could not find suitable matches. '
                'Please try again.'
            )
        })

    # Save search description in history
    query = (
        f"{profile.target_role} | "
        f"{', '.join(work_modes)} | "
        f"{profile.preferred_location}"
    )

    models.SearchHistory.objects.create(
        user=user,
        query=query,
        results_count=len(matched_jobs),
        results=matched_jobs
    )

    # Keep jobs available for Job Details
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

    user = models.get_user_by_id(
        request.session['user_id']
    )

    job_id = request.POST.get(
        'job_id',
        ''
    )

    job_url = request.POST.get(
        'job_url',
        ''
    )

    jobs = request.session.get(
        'jobs',
        []
    )

    job = None

    # Try to find the job in the current search session
    if job_id:
        job = next(
            (
                job_item
                for job_item in jobs
                if job_item.get('job_id') == job_id
            ),
            None
        )

    # If not found, try Saved Jobs
    if not job and job_url:
        favorite = models.Favorite.objects.filter(
            user=user,
            job_url=job_url
        ).first()

        if favorite:
            job = {
                'job_id': '',
                'title': favorite.job_title,
                'company': favorite.company,
                'location': favorite.location or '',
                'description': (
                    favorite.job_description or ''
                ),
                'apply_link': favorite.job_url,
            }

    if not job or not job.get('apply_link'):
        messages.error(
            request,
            'Job not found, please search again'
        )
        return redirect('/dashboard')

    # Prevent duplicate applications
    if models.has_applied(
        user.id,
        job['apply_link']
    ):
        messages.error(
            request,
            'You already applied to this job'
        )
        return redirect('/dashboard')

    models.create_application(
        user,
        job
    )

    messages.success(
        request,
        'Job added to My Applications'
    )

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
        messages.error(
            request,
            'Application not found'
        )
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

    # Get latest saved AI results for this job
    cv_review = models.AIReview.objects.filter(
        user=user,
        job_url=application.job_url,
        review_type='cv'
    ).order_by('-created_at').first()

    cover_review = models.AIReview.objects.filter(
        user=user,
        job_url=application.job_url,
        review_type='cover_letter'
    ).order_by('-created_at').first()

    interview_review = models.AIReview.objects.filter(
        user=user,
        job_url=application.job_url,
        review_type='interview'
    ).order_by('-created_at').first()

    context = {
        'user': user,
        'job': job,
        'applied': True,
        'cv_review': cv_review,
        'cover_review': cover_review,
        'interview_review': interview_review,
    }

    return render(
        request,
        'job_details.html',
        context
    )

def remove_application(request, id):
    if 'user_id' not in request.session:
        return redirect('/login')

    if request.method != 'POST':
        return redirect('/dashboard')

    user = models.get_user_by_id(request.session['user_id'])

    application = models.Application.objects.filter(
        id=id,
        user=user
    ).first()

    if not application:
        messages.error(request, 'Application not found')
        return redirect('/dashboard')

    application.delete()

    messages.success(request, 'Application removed successfully')
    return redirect('/dashboard')

def update_application_status(request, id):
    if 'user_id' not in request.session:
        return redirect('/login')

    if request.method != 'POST':
        return redirect('/dashboard')

    user = models.get_user_by_id(request.session['user_id'])

    application = models.Application.objects.filter(
        id=id,
        user=user
    ).first()

    if not application:
        messages.error(request, 'Application not found')
        return redirect('/dashboard')

    new_status = request.POST.get('status')

    allowed_statuses = [
        'applied',
        'interview',
        'accepted',
        'rejected',
    ]

    if new_status in allowed_statuses:
        application.status = new_status
        application.save()

    return redirect('/dashboard')

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

    favorite = models.Favorite.objects.filter(
        id=id,
        user=user
    ).first()

    if not favorite:
        messages.error(
            request,
            'Job not found'
        )
        return redirect('/favorites')

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

    # Get latest saved AI results for this job
    cv_review = models.AIReview.objects.filter(
        user=user,
        job_url=favorite.job_url,
        review_type='cv'
    ).order_by('-created_at').first()

    cover_review = models.AIReview.objects.filter(
        user=user,
        job_url=favorite.job_url,
        review_type='cover_letter'
    ).order_by('-created_at').first()

    interview_review = models.AIReview.objects.filter(
        user=user,
        job_url=favorite.job_url,
        review_type='interview'
    ).order_by('-created_at').first()

    context = {
        'user': user,
        'job': job,
        'applied': models.has_applied(
            user.id,
            favorite.job_url
        ),
        'favorite_id': favorite.id,
        'cv_review': cv_review,
        'cover_review': cover_review,
        'interview_review': interview_review,
    }

    return render(
        request,
        'job_details.html',
        context
    )

def remove_favorite(request, id):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('/login')

    if request.method == 'POST':
        models.Favorite.objects.filter(id=id, user_id=request.session['user_id']).delete()
    return redirect('/favorites')  

def search_history(request):
    if 'user_id' not in request.session:
        return redirect('/login')

    user = models.get_user_by_id(request.session['user_id'])

    if user.role != 'user':
        return redirect('/admin-dashboard')

    searches = models.SearchHistory.objects.filter(
        user=user
    ).order_by('-created_at')

    context = {
        'user': user,
        'searches': searches,
    }

    return render(request, 'search_history.html', context)

def open_search(request, id):
    if 'user_id' not in request.session:
        return redirect('/login')

    user = models.get_user_by_id(request.session['user_id'])

    search = models.SearchHistory.objects.filter(
        id=id,
        user=user
    ).first()

    if not search:
        messages.error(request, 'Search not found')
        return redirect('/history')

    # Keep old results available for Job Details
    request.session['jobs'] = search.results

    context = {
        'user': user,
        'search': search,
        'jobs': search.results,
    }

    return render(request, 'search_results.html', context)  

def clear_history(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('/login')

    if request.method == 'POST':
        models.SearchHistory.objects.filter(user_id=request.session['user_id']).delete()
    return redirect('/history')