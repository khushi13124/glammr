from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import update_session_auth_hash
from .models import UserProfile

def auth_view(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'signup':
            username = request.POST.get('username')
            email = request.POST.get('email')
            mobile_no = request.POST.get('mobile_no') ###
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')

            if password1 != password2:
                messages.error(request, "Passwords do not match.")
                return render(request, 'auth.html', {'show_signup': True})

            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already taken.")
                return render(request, 'auth.html', {'show_signup': True})

            user = User.objects.create_user(username=username, email=email, password=password1)

            user.userprofile.mobile_no = mobile_no ###
            user.userprofile.save() ###

            login(request, user)
            return redirect('index')  # Redirect to index after successful signup

        elif form_type == 'login':
            username = request.POST.get('username')
            password = request.POST.get('password')

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')  # Redirect to index after successful login
            else:
                messages.error(request, "Invalid credentials.")
                return render(request, 'auth.html', {'show_signup': False})

    # GET request
    return render(request, 'auth.html', {'show_signup': False})


@login_required(login_url='/auth/')
def index_view(request):
    return render(request, 'index.html')

def logout_view(request):
    logout(request)
    return redirect('/auth/')

@csrf_exempt
@login_required(login_url='/auth/')
def update_privacy_setting(request):
    if request.method == "POST":
        data = json.loads(request.body)
        is_private = data.get("is_private", False)
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        user_profile.is_private = is_private
        user_profile.save()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)

@login_required(login_url='/auth/')
def my_account_view(request):
    # Get or create user profile to avoid RelatedObjectDoesNotExist
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    # Compute initial stats accurately
    from api.models import Board, Upload, Inspo
    my_saves_board = Board.get_default_board(request.user)
    total_saves = my_saves_board.inspos.filter(is_deleted=False).count()
    total_uploads = Upload.objects.filter(user=request.user).count()
    total_boards = Board.objects.filter(user=request.user, is_deleted=False).count()
    
    context = {
        "user": request.user,
        "user_profile": user_profile,
        "total_saves": total_saves,
        "total_uploads": total_uploads,
        "total_boards": total_boards,
        "my_saves_board_id": my_saves_board.id,
        "show_email": user_profile.show_email_on_profile,
    }
    return render(request, "myaccount.html", context)

@csrf_exempt
@login_required(login_url='/auth/')
def toggle_show_email(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        user_profile.show_email_on_profile = data.get("show_email", True)
        user_profile.save()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "fail"}, status=400)

@login_required(login_url='/auth/')
def edit_profile_view(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST' and 'profile_picture' in request.FILES:
        user_profile.profile_picture = request.FILES['profile_picture']
        user_profile.save()
    return redirect('myaccount')

@login_required(login_url='/auth/')
def settings_page_view(request):
    return render(request, 'settings.html')


@login_required(login_url='/auth/')
def custom_password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been updated successfully!')
            return redirect('settings')
        else:
            messages.error(request, 'Please correct the errors below.')
            request.session['password_form_errors'] = form.errors.get_json_data()
            return redirect('settings')
    return redirect('settings')

@login_required(login_url='/auth/')
def settings_page_view(request):
    form_errors = request.session.pop('password_form_errors', None)
    return render(request, 'settings.html', {
        'password_form_errors': form_errors
    })


@login_required(login_url='/auth/')
def delete_account_view(request):
    if request.method == 'POST':
        user = request.user
        logout(request)           # log the user out first
        user.delete()             # delete the user from DB
        messages.success(request, "Your account has been permanently deleted.")
        return redirect('auth')   # redirect to your login page
    else:
        return redirect('settings')  # fallback if accessed via GET