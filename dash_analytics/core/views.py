from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from .models import UserProfile
import requests
import json


def index(request):
    """
    Landing page view
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/index.html')


@login_required
def dashboard(request):
    """
    Main dashboard view
    """
    # Get user theme preference
    theme = get_theme_preference(request)

    # Context data for the dashboard
    context = {
        'title': 'Dashboard',
        'active_page': 'dashboard',
        'theme': theme
    }

    return render(request, 'core/dashboard.html', context)


@login_required
def sales_trend(request):
    """
    Sales trend analysis view
    """
    # Get user theme preference
    theme = get_theme_preference(request)

    # Context data for sales trend
    context = {
        'title': 'Sales Trend',
        'active_page': 'sales_trend',
        'theme': theme
    }

    return render(request, 'core/sales_trend.html', context)


@login_required
def product_performance(request):
    """
    Product performance analysis view
    """
    # Get user theme preference
    theme = get_theme_preference(request)

    # Context data for product performance
    context = {
        'title': 'Product Performance',
        'active_page': 'product_performance',
        'theme': theme
    }

    return render(request, 'core/product_performance.html', context)


@login_required
def demographics(request):
    """
    Customer demographics view
    """
    # Get user theme preference
    theme = get_theme_preference(request)

    # Context data for demographics
    context = {
        'title': 'Customer Demographics',
        'active_page': 'demographics',
        'theme': theme
    }

    return render(request, 'core/demographics.html', context)


@login_required
def geographical_insights(request):
    """
    Geographical insights view
    """
    # Get user theme preference
    theme = get_theme_preference(request)

    # Context data for geographical insights
    context = {
        'title': 'Geographical Insights',
        'active_page': 'geographical_insights',
        'theme': theme
    }

    return render(request, 'core/geographical_insights.html', context)


@login_required
def customer_behavior(request):
    """
    Customer behavior analysis view
    """
    # Get user theme preference
    theme = get_theme_preference(request)

    # Context data for customer behavior
    context = {
        'title': 'Customer Behavior',
        'active_page': 'customer_behavior',
        'theme': theme
    }

    return render(request, 'core/customer_behavior.html', context)


@login_required
def prediction(request):
    """
    Prediction view
    """
    # Get user theme preference
    theme = get_theme_preference(request)

    # Context data for prediction
    context = {
        'title': 'Predictions',
        'active_page': 'prediction',
        'theme': theme
    }

    return render(request, 'core/prediction.html', context)


@login_required
def data_upload(request):
    """
    Data upload view
    """
    # Get user theme preference
    theme = get_theme_preference(request)

    # Context data for data upload
    context = {
        'title': 'Data Upload',
        'active_page': 'data_upload',
        'theme': theme
    }

    return render(request, 'core/data_upload.html', context)

# Authentication Views


def signin(request):
    """
    Sign in view
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}.")
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'core/signin.html', {'form': form})


def signup(request):
    """
    Sign up view
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Create user profile with default theme preference
            UserProfile.objects.create(user=user, theme_preference='light')

            login(request, user)
            messages.success(
                request, "Registration successful. You are now logged in.")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid form submission.")
    else:
        form = UserCreationForm()

    return render(request, 'core/signup.html', {'form': form})


@login_required
def logout_view(request):
    """
    Logout view
    """
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('signin')


@login_required
def profile(request):
    """
    User profile view
    """
    # Get user theme preference
    theme = get_theme_preference(request)

    # Handle form submissions
    if request.method == 'POST':
        # Check which form was submitted
        if 'action' in request.POST:
            action = request.POST.get('action')

            # Handle profile update
            if action == 'update_profile':
                # Update user's profile information
                user = request.user
                user.email = request.POST.get('email', user.email)
                user.first_name = request.POST.get(
                    'first_name', user.first_name)
                user.last_name = request.POST.get('last_name', user.last_name)
                user.save()

                messages.success(request, "Profile updated successfully.")

            # Handle password change
            elif action == 'change_password':
                current_password = request.POST.get('current_password')
                new_password = request.POST.get('new_password')
                confirm_password = request.POST.get('confirm_password')

                # Verify current password
                if not request.user.check_password(current_password):
                    messages.error(request, "Current password is incorrect.")
                # Verify new passwords match
                elif new_password != confirm_password:
                    messages.error(request, "New passwords do not match.")
                # Verify new password is not empty
                elif not new_password:
                    messages.error(request, "New password cannot be empty.")
                else:
                    # Change password
                    request.user.set_password(new_password)
                    request.user.save()
                    # Re-authenticate the user to prevent logout
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "Password changed successfully.")

        # Handle theme toggle
        elif 'theme' in request.POST:
            new_theme = request.POST.get('theme', 'light')
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                user_profile.theme_preference = new_theme
                user_profile.save()
                theme = new_theme
                messages.info(request, f"Theme changed to {new_theme} mode.")
            except UserProfile.DoesNotExist:
                # Create a profile with the specified theme
                UserProfile.objects.create(
                    user=request.user, theme_preference=new_theme)
                theme = new_theme

    # Context data for profile
    context = {
        'title': 'Profile',
        'active_page': 'profile',
        'theme': theme
    }

    return render(request, 'core/profile.html', context)

# Helper functions


def get_theme_preference(request):
    """
    Helper function to get user theme preference
    """
    default_theme = 'light'

    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            return profile.theme_preference
        except UserProfile.DoesNotExist:
            # Create a profile with default theme if it doesn't exist
            UserProfile.objects.create(
                user=request.user, theme_preference=default_theme)

    return default_theme
