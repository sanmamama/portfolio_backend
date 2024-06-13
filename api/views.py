from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User
from .serializer import UserSerializer
from django.views.generic import TemplateView

class IndexView(TemplateView):
    template_name= 'index.html'

class UserViewSet(APIView):
    def get(self, request):
        user = User.objects.all()
        serializer = UserSerializer(user, many=True)
        return Response(serializer.data)