from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.hashers import check_password, make_password
from .models import MongoUser, Customer, Product, Order, Sales
from analytics.models import (
    ProductPerformance, CategoryPerformance, Demographics, 
    GeographicalInsights, CustomerBehavior, Prediction, SalesTrend
)
from api.serializers.user_serializer import UserSerializer
import jwt
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone


def initialize_data():
    """
    Initialize database collections if they don't exist.
    This function ensures all required collections are created in MongoDB,
    but does not add any sample data.
    """
    try:
        # Ensure core collections exist by touching them
        MongoUser.objects().first()
        Customer.objects().first()
        Product.objects().first()
        Order.objects().first()
        Sales.objects().first()
        
        # Ensure analytics collections exist by touching them
        SalesTrend.objects().first()
        ProductPerformance.objects().first()
        CategoryPerformance.objects().first()
        Demographics.objects().first()
        GeographicalInsights.objects().first()
        CustomerBehavior.objects().first()
        Prediction.objects().first()

        print("Successfully initialized all MongoDB collections")

    except Exception as e:
        print(f"Error ensuring collections exist: {str(e)}")
        # Don't raise the error since we just want to ensure collections exist


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
    Dashboard view
    """
    initialize_data()  # Ensure we have initial data

    if not request.user.is_authenticated:
        return redirect('login')

    try:
        # Add your dashboard context data here
        context = {
            'user': request.user,
            'theme': get_theme_preference(request),
        }
        return render(request, 'core/dashboard.html', context)
    except Exception as e:
        messages.error(request, f"Error loading dashboard: {str(e)}")
        return redirect('index')


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
    try:
        user_id = request.session.get('_auth_user_id')
        if user_id:
            user = MongoUser.objects(id=user_id).first()
            if user:
                return redirect('dashboard')

        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')

            if not username or not password:
                messages.error(request, 'Please provide both username and password.')
                return render(request, 'core/signin.html')

            user = MongoUser.objects.filter(username=username).first()

            if not user or not user.check_password(password):
                messages.error(request, 'Invalid username or password.')
                return render(request, 'core/signin.html')

            if not user.is_active:
                messages.error(request, 'This account is inactive.')
                return render(request, 'core/signin.html')

            # 🛠 Set session manually
            request.session['_auth_user_id'] = str(user.pk)
            request.session['_auth_user_backend'] = 'core.auth.MongoDBAuthBackend'
            request.session['_auth_user_hash'] = ''

            # Update last login
            user.last_login = datetime.utcnow()
            user.save(skip_password_hash=True)

            return redirect('dashboard')

    except Exception as e:
        print(f"Signin error: {str(e)}")
        messages.error(request, 'An error occurred during login. Please try again.')

    return render(request, 'core/signin.html')



def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if not all([username, password1, password2]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('signup')

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return redirect('signup')

        try:
            if MongoUser.objects.filter(username=username).first():
                messages.error(request, 'Username already exists.')
                return redirect('signup')

            if email and MongoUser.objects.filter(email=email).first():
                messages.error(request, 'Email already exists.')
                return redirect('signup')

            user = MongoUser(
                username=username,
                email=email if email else None,
                password=password1  # will be hashed automatically
            )
            user.save()

            # 🛠 Set session manually
            request.session['_auth_user_id'] = str(user.pk)
            request.session['_auth_user_backend'] = 'core.auth.MongoDBAuthBackend'
            request.session['_auth_user_hash'] = ''

            messages.success(request, 'Registration successful! Welcome!')
            return redirect('dashboard')

        except Exception as e:
            print(f"Signup error: {str(e)}")
            messages.error(request, 'An error occurred during registration. Please try again.')
            return redirect('signup')

    return render(request, 'core/signup.html')


@login_required
def logout_view(request):
    """
    Logout view
    """
    # Clear session
    request.session.flush()
    messages.info(request, "You have successfully logged out.")
    return redirect('signin')


@login_required
def profile(request):
    """
    User profile view
    """
    # Get user theme preference from session
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
                user.first_name = request.POST.get('first_name', user.first_name)
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
            request.session['theme'] = new_theme
            theme = new_theme
            messages.info(request, f"Theme changed to {new_theme} mode.")

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
    Helper function to get user theme preference from session
    """
    return request.session.get('theme', 'light')
