from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser
from bson import ObjectId
from django.conf import settings
from .models import MongoUser
from mongoengine import get_db

class MongoDBAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        if not username or not password:
            return None

        try:
            # Use the existing connection
            user = MongoUser.objects.filter(username=username).first()
            if user and user.check_password(password):
                return user
        except Exception as e:
            print(f"Authentication error: {str(e)}")
        return None

    def get_user(self, user_id):
        try:
            return MongoUser.objects.get(id=ObjectId(user_id))
        except (MongoUser.DoesNotExist, Exception):
            return None