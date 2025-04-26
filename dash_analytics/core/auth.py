from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser
from bson import ObjectId
from django.conf import settings
from .models import MongoUser

class MongoDBAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        if not username or not password:
            return None

        user = MongoUser.objects.filter(username=username).first()
        if user and user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return MongoUser.objects.get(id=ObjectId(user_id))
        except (MongoUser.DoesNotExist, Exception):
            return None