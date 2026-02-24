
from django.urls import path
from . import views

app_name = 'schools'

urlpatterns = [
    # School list and detail (Read)
    path('', views.schools_list, name='schools_list'),
    path('<int:pk>/', views.school_detail, name='school_detail'),
    
    # School edit (Update)
    path('<int:pk>/edit/', views.school_edit, name='school_edit'),
    
    # Notes (Create, Update, Delete)
    path('<int:school_pk>/notes/add/', views.note_create, name='note_create'),
    path('notes/<int:pk>/edit/', views.note_edit, name='note_edit'),
    path('notes/<int:pk>/delete/', views.note_delete, name='note_delete'),
]