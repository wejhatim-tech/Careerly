from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from urllib.parse import quote
from . import models

CONTACT_FIELDS = ['name', 'email', 'subject', 'message']
REGISTER_FIELDS = ['first_name', 'last_name', 'email']


# ---------- Helpers ----------

def get_logged_user(request):
    # Logged in user, or None
    return models.get_user(request.session.get('user_id'))


def show_errors(request, errors):
    for value in errors.values():
        messages.error(request, value)


def keep_inputs(request, prefix, fields):
    # Save form input in the session so the user does not retype it
    for field in fields:
        request.session[prefix + field] = request.POST[field]


def clear_inputs(request, prefix, fields):
    for field in fields:
        request.session.pop(prefix + field, None)


def get_session_job(request, job_id):
    return models.find_job(request.session.get('jobs', []), job_id)


def render_job(request, user, job, **extra):
    # All job pages use the same template with the saved AI results
    context = {'user': user, 'job': job}
    context.update(models.get_ai_reviews(user, job.get('apply_link', '')))
    context.update(extra)
    return render(request, 'job_details.html', context)


# ---------- Access checks (decorators) ----------

def user_required(view):
    # Only logged in normal users, the user is passed to the view
    def wrapper(request, *args, **kwargs):
        user = get_logged_user(request)
        if not user:
            return redirect('/login')
        if user.role != 'user':
            return redirect('/admin-dashboard')
        return view(request, user, *args, **kwargs)
    return wrapper


def admin_required(view):
    # Only logged in admins, the admin is passed to the view
    def wrapper(request, *args, **kwargs):
        admin = get_logged_user(request)
        if not admin:
            return redirect('/login')
        if admin.role != 'admin':
            return redirect('/dashboard')
        return view(request, admin, *args, **kwargs)
    return wrapper


def ajax_user_required(view):
    # Same check for fetch requests, answers with JSON
    def wrapper(request, *args, **kwargs):
        user = get_logged_user(request)
        if not user:
            return JsonResponse({'success': False, 'message': 'Please log in first'}, status=401)
        if request.method != 'POST':
            return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)
        if user.role != 'user':
            return JsonResponse({'success': False, 'message': 'Access denied'}, status=403)
        return view(request, user, *args, **kwargs)
    return wrapper


# ---------- Public pages ----------

def index(request):
    return render(request, 'index.html')


def about(request):
    return render(request, 'about.html')


def register(request):
    if request.method != 'POST':
        return render(request, 'register.html')

    errors = models.User.objects.reg_validation(request.POST)
    if errors:
        keep_inputs(request, '', REGISTER_FIELDS)
        show_errors(request, errors)
        return redirect('/register')

    user = models.create_user(request.POST)
    request.session['user_id'] = user.id
    clear_inputs(request, '', REGISTER_FIELDS)
    return redirect('/profile')


def login(request):
    if request.method != 'POST':
        return render(request, 'login.html')

    errors = models.User.objects.login_validation(request.POST)
    if errors:
        keep_inputs(request, 'login_', ['email'])
        show_errors(request, errors)
        return redirect('/login')

    user = models.get_user_by_email(request.POST['email'])
    request.session['user_id'] = user.id
    clear_inputs(request, 'login_', ['email'])
    return redirect('/admin-dashboard' if user.role == 'admin' else '/dashboard')


def logout(request):
    request.session.flush()
    return redirect('/')


def contact(request):
    if request.method != 'POST':
        return render(request, 'contact.html')

    errors = models.ContactMessage.objects.contact_validation(request.POST)
    if errors:
        keep_inputs(request, 'contact_', CONTACT_FIELDS)
        show_errors(request, errors)
        return redirect('/contact')

    models.create_contact_message(request.POST)
    clear_inputs(request, 'contact_', CONTACT_FIELDS)
    messages.success(request, 'Your message has been sent successfully!')
    return redirect('/contact')


# ---------- Admin ----------

@admin_required
def admin_dashboard(request, admin):
    search = request.GET.get('search', '')
    context = {'admin': admin, 'users': models.search_users(search), 'search': search}
    context.update(models.admin_stats())
    return render(request, 'admin_dashboard.html', context)


@admin_required
def admin_user(request, admin, id):
    user = models.get_user(id)
    if not user:
        messages.error(request, 'User not found')
        return redirect('/admin-dashboard')
    return render(request, 'admin_user.html', {'admin': admin, 'user': user})


@admin_required
def toggle_user_status(request, admin, id):
    user = models.get_user(id)
    if request.method != 'POST' or not user:
        return redirect('/admin-dashboard')

    # Admin can't deactivate himself
    if user.id == admin.id:
        messages.error(request, 'You cannot deactivate your own account')
    else:
        models.switch_user_status(user)
        messages.success(request, 'Account activated' if user.status == 'active' else 'Account deactivated')
    return redirect(f'/admin-dashboard/user/{id}')


@admin_required
def admin_message(request, admin, id):
    msg = models.get_contact_message(id)
    if not msg:
        messages.error(request, 'Message not found')
        return redirect('/admin-dashboard')
    return render(request, 'admin_message.html', {'admin': admin, 'msg': msg})


@admin_required
def remove_admin_message(request, admin, id):
    if request.method == 'POST' and models.remove_contact_message(id):
        messages.success(request, 'Message removed successfully')
    return redirect('/admin-dashboard')


# ---------- Profile and skills ----------

@user_required
def profile(request, user):
    context = {
        'user': user,
        'profile': models.get_profile_by_user(user.id),
        'skills': models.get_user_skills(user.id),
        'edit_mode': request.GET.get('edit') == 'true',
    }
    return render(request, 'profile.html', context)


@user_required
def create_profile(request, user):
    # Only one profile for each user
    if request.method == 'POST' and not models.get_profile_by_user(user.id):
        errors = models.Profile.objects.profile_validation(request.POST)
        if errors:
            show_errors(request, errors)
        else:
            models.create_profile(user, request.POST)
    return redirect('/profile')


@user_required
def edit_profile(request, user):
    profile = models.get_profile_by_user(user.id)
    if not profile:
        return redirect('/profile')
    if request.method != 'POST':
        return redirect('/profile?edit=true')

    errors = models.Profile.objects.profile_validation(request.POST)
    if errors:
        show_errors(request, errors)
        return redirect('/profile?edit=true')

    models.update_profile(profile, request.POST)
    return redirect('/profile')


@ajax_user_required
def add_skill(request, user):
    skill_name = request.POST.get('skill', '').strip()
    if not skill_name:
        return JsonResponse({'success': False, 'message': 'Skill is required'})

    skill = models.add_user_skill(user, skill_name)
    return JsonResponse({'success': True, 'skill_id': skill.id, 'skill_name': skill.name})


@ajax_user_required
def remove_skill(request, user, skill_id):
    models.remove_user_skill(user.id, skill_id)
    return JsonResponse({'success': True})


# ---------- Dashboard and jobs ----------

@user_required
def dashboard(request, user):
    profile = models.get_profile_by_user(user.id)
    # User must complete profile first
    if not profile:
        return redirect('/profile')

    context = {
        'user': user,
        'profile': profile,
        'skills': models.get_user_skills(user.id),
        'applications': models.get_user_applications(user.id),
        'saved_jobs': request.session.get('jobs', []),
    }
    return render(request, 'dashboard.html', context)


@ajax_user_required
def find_jobs(request, user):
    profile = models.get_profile_by_user(user.id)
    if not profile:
        return JsonResponse({'success': False, 'message': 'Please complete your profile first'})

    data = models.find_matched_jobs(user, profile)
    if data['success']:
        # Save jobs in session for Job Details page
        request.session['jobs'] = data['jobs']
    return JsonResponse(data)


@user_required
def job_details(request, user):
    job = get_session_job(request, request.GET.get('id', ''))
    if not job:
        messages.error(request, 'Job not found, please search again')
        return redirect('/dashboard')

    job_url = job.get('apply_link', '')
    return render_job(request, user, job,
        applied=models.has_applied(user.id, job_url),
        favorite=models.is_favorite(user.id, job_url))


@ajax_user_required
def job_ai(request, user):
    job, application = models.get_ai_job(
        user,
        request.session.get('jobs', []),
        request.POST.get('job_id', ''),
        request.POST.get('job_url', ''),
    )
    if not job:
        return JsonResponse({'success': False, 'message': 'Job not found'})

    data = models.run_ai_tool(
        user, job, application,
        request.POST.get('tool', ''),
        request.FILES.get('file'),
        request.POST.get('text_content', '').strip(),
    )
    return JsonResponse(data)


@user_required
def download_ai_file(request, user, id):
    review = models.get_user_review(user, id)
    if not review or not review.uploaded_file:
        messages.error(request, 'File not found')
        return redirect('/dashboard')
    return FileResponse(review.uploaded_file.open('rb'), as_attachment=True, filename=review.file_name)


# ---------- Applications ----------

@user_required
def apply_job(request, user):
    if request.method == 'POST':
        job = get_session_job(request, request.POST.get('job_id'))
        if not job or not job.get('apply_link'):
            messages.error(request, 'Job not found, please search again')
        elif models.apply_job(user, job):
            messages.success(request, 'Job added to My Applications')
        else:
            messages.error(request, 'You already applied to this job')
    return redirect('/dashboard')


@user_required
def application_details(request, user, id):
    application = models.get_user_application(user, id)
    if not application:
        messages.error(request, 'Application not found')
        return redirect('/dashboard')

    job = models.saved_job_dict(application, 'This job was saved in your applications.')
    return render_job(request, user, job, applied=True)


@user_required
def remove_application(request, user, id):
    if request.method == 'POST':
        if models.remove_application(user, id):
            messages.success(request, 'Application removed successfully')
        else:
            messages.error(request, 'Application not found')
    return redirect('/dashboard')


@user_required
def update_application_status(request, user, id):
    if request.method == 'POST':
        application = models.get_user_application(user, id)
        if application:
            models.update_application_status(application, request.POST.get('status'))
        else:
            messages.error(request, 'Application not found')
    return redirect('/dashboard')


# ---------- Favorites ----------

@user_required
def saved_jobs(request, user):
    context = {'user': user, 'favorites': models.get_user_favorites(user.id)}
    return render(request, 'saved_jobs.html', context)


@user_required
def favorite_job(request, user):
    if request.method != 'POST':
        return redirect('/dashboard')

    job_id = request.POST.get('job_id', '')
    job = get_session_job(request, job_id)
    if not job or not job.get('apply_link'):
        messages.error(request, 'Job not found, please search again')
        return redirect('/dashboard')

    models.toggle_favorite(user, job)
    return redirect(f'/job?id={quote(job_id)}')


@user_required
def favorite_details(request, user, id):
    favorite = models.get_user_favorite(user, id)
    if not favorite:
        messages.error(request, 'Job not found')
        return redirect('/favorites')

    job = models.saved_job_dict(favorite, 'This job was saved in your favourites.')
    return render_job(request, user, job,
        applied=models.has_applied(user.id, favorite.job_url),
        favorite_id=favorite.id)


@user_required
def remove_favorite(request, user, id):
    if request.method == 'POST':
        models.remove_favorite(user, id)
    return redirect('/favorites')


# ---------- Search history ----------

@user_required
def search_history(request, user):
    context = {'user': user, 'searches': models.get_search_history(user)}
    return render(request, 'search_history.html', context)


@user_required
def open_search(request, user, id):
    search = models.get_user_search(user, id)
    if not search:
        messages.error(request, 'Search not found')
        return redirect('/history')

    # Keep old results available for Job Details
    request.session['jobs'] = search.results
    context = {'user': user, 'search': search, 'jobs': search.results}
    return render(request, 'search_results.html', context)


@user_required
def clear_history(request, user):
    if request.method == 'POST':
        models.clear_search_history(user)
    return redirect('/history')
