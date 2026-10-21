from django.shortcuts import render, redirect
from django.contrib import messages
from . import models


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