from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.hashers import check_password
from datetime import datetime
from core.models import MongoUser
from api.serializers.user_serializer import UserSerializer
import jwt
from django.conf import settings

@api_view(['POST'])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        # Check if user already exists
        if MongoUser.objects.filter(username=serializer.validated_data['username']).first():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
        if MongoUser.objects.filter(email=serializer.validated_data['email']).first():
            return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create new user
        user = serializer.create(serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = MongoUser.objects.filter(username=username).first()
    if user and check_password(password, user.password):
        # Update last login
        user.last_login = datetime.utcnow()
        user.save()
        
        # Generate JWT token
        token = jwt.encode({
            'user_id': str(user.id),
            'username': user.username,
            'email': user.email,
            'exp': datetime.utcnow() + settings.JWT_EXPIRATION_DELTA
        }, settings.SECRET_KEY, algorithm='HS256')
        
        return Response({
            'token': token,
            'user': UserSerializer(user).data
        })
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
def logout(request):
    # Client should remove the token
    return Response({'message': 'Successfully logged out'})