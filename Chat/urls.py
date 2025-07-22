from django.urls import path
from .views import *

urlpatterns = [
path('',CreateRoom,name='create-group'),
path('<str:group_name>/<str:user_name>/',MessageView,name='group'),
]