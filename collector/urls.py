from django.urls import path

from . import views

app_name = 'collector'
urlpatterns = [
    path('', views.index, name='index'),
    path('job/<uuid:uuid>/', views.job, name='job')
]
