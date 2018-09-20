from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('collector/', include('collector.urls')),
    path('admin/', admin.site.urls)
]
