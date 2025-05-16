"""
MongoDB Authentication Backend for Django 5.x

This module provides an authentication backend for Django that uses
MongoDB for user authentication.
"""

from .models import MongoUser
from django.utils.timezone import now


class MongoDBAuthBackend:
    """
    Custom authentication backend for Django that uses MongoDB.
    Compatible with Django 5.x
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a user based on username and password.
        
        Args:
            request: The request object
            username: The username to authenticate
            password: The password to check
            **kwargs: Additional arguments
            
        Returns:
            MongoUser: The authenticated user or None
        """
        user = MongoUser.objects.filter(username=username).first()
        
        if user is not None and user.check_password(password):
            user.last_login = now()
            user.save(skip_password_hash=True)
            return user
            
        return None
        
    def get_user(self, user_id):
        """
        Get a user by ID.
        
        Args:
            user_id: The ID of the user to retrieve
            
        Returns:
            MongoUser: The user or None
        """
        try:
            return MongoUser.objects.get(id=user_id)
        except MongoUser.DoesNotExist:
            return None
