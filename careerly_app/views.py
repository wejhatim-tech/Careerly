from django.shortcuts import render, redirect
from django.contrib import messages
from . import models
from django.http import JsonResponse


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