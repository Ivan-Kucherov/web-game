from django.urls import path
from rest_framework import routers
from webgame.game import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


router = routers.SimpleRouter()

urlpatterns = [
    path('atest/',views.Atest.as_view()),
    path('creategame/',views.CreateGame.as_view()),
    path('register/', views.RegisterAPI.as_view(), name='register'),
    path('login/', views.LoginAPI.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('players/', views.ListPlayers.as_view()), 
    path('player/<str:uname>/', views.Player_.as_view()),
    path('user/<str:uname>/', views.User_.as_view()),
    path('api/token/obtain', TokenObtainPairView.as_view(), name='token_obtain'),
]

urlpatterns += router.urls