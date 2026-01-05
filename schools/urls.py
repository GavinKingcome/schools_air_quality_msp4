
from django.urls import path
from . import views

app_name = 'schools'

urlpatterns = [
    path('', views.schools_list, name='schools_list'),
    path('login/', views.login_view, name='login'),
]