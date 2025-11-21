from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload_strategy/', views.upload_strategy, name='upload_strategy'),
    path('candidates/<cap_id>/<skill_id>/', views.candidates, name='candidates'),
    path('roadmap/<cap_id>/<skill_id>/<emp_id>/', views.roadmap, name='roadmap'),
]
