import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from .models import MongoUser
from django.utils.functional import SimpleLazyObject
from django.contrib import messages

def get_user_from_token(request):
    token = request.session.get('auth_token')
    if not token:
        return AnonymousUser()
    
    try:
        # Decode the JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        user = MongoUser.objects.filter(id=payload['user_id']).first()
        if user:
            return user
    except jwt.ExpiredSignatureError:
        # Token has expired
        request.session.flush()
        messages.error(request, "Session expired. Please sign in again.")
    except jwt.InvalidTokenError:
        # Token is invalid
        request.session.flush()
        messages.error(request, "Invalid session. Please sign in again.")
    except Exception:
        request.session.flush()
    
    return AnonymousUser()

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = SimpleLazyObject(lambda: get_user_from_token(request))
        return self.get_response(request)