from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView

# Create your views here.
#class Register()
class Print(APIView):
    def get(self, request, format=None):
        print(request)
        return Response(str(request.data))
    def post(self, request, format=None):
        print(request)
        return Response(str(request))
