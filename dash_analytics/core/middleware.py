import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from .models import MongoUser
from django.utils.functional import SimpleLazyObject
from django.contrib import messages


def get_user_from_session(request):
    user_id = request.session.get('_auth_user_id')
    if not user_id:
        return AnonymousUser()

    try:
        # Use the existing connection from settings.py
        user = MongoUser.objects.filter(id=user_id).first()
        if user:
            return user
    except Exception as e:
        print(f"Session error: {str(e)}")
    return AnonymousUser()

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = SimpleLazyObject(lambda: get_user_from_session(request))
        return self.get_response(request)
