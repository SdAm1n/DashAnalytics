from django.contrib.auth.backends import BaseBackend
from .models import MongoUser

class MongoEngineBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        try:
            user = MongoUser.objects.get(username=username)
            if user.check_password(password):
                return user
        except MongoUser.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        try:
            return MongoUser.objects.get(id=user_id)
        except MongoUser.DoesNotExist:
            return None