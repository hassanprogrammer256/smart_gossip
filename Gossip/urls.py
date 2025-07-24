# chatapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
   path('chat/', views.index, name='index'),
   path('chat/<str:group_name>/', views.group, name='group'),
   path('stream_webhook/', views.stream_webhook, name='stream_webhook'),
]