from django.shortcuts import render, redirect
from django.contrib import messages
from . import models
from django.db.models import Q


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
            # منحفظ اللي كتبه لحتى ما يرجع يكتبه
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
        # منمسح البيانات المحفوظة بعد النجاح
        for key in ['contact_name', 'contact_email', 'contact_subject', 'contact_message']:
            request.session.pop(key, None)
        messages.success(request, 'Your message has been sent successfully!')
        return redirect('/contact')

    return render(request, 'contact.html')


def admin_dashboard(request):
    if 'user_id' not in request.session:
        return redirect('/login')

    admin = models.User.objects.get(id=request.session['user_id'])
    # اليوزر العادي ما بيفوت هون
    if admin.role != 'admin':
        return redirect('/dashboard')

    # البحث بالاسم أو الإيميل
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