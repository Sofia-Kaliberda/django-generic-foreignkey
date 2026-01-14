"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView
from action_logs import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('logs/', views.ActionLogListView.as_view(), name='log_list'),
    path('logs/<uuid:pk>', views.ActionLogDetailView.as_view(), name='log_detail'),
    path('logs/object/<int:content_type_id>/<str:object_id>/', 
        views.ObjectLogListView.as_view(), name='object_logs'),


    path('blogs/', views.BlogListView.as_view(), name='blog_list'),
    path('blogs/<int:pk>/', views.BlogDetailView.as_view(), name='blog_detail'),
    path('blogs/create/', views.BlogCreateView.as_view(), name='blog_create'),
    path('blogs/<int:pk>/update/', views.BlogUpdateView.as_view(), name='blog_update'),
    path('blogs/<int:pk>/delete/', views.BlogDeleteView.as_view(), name='blog_delete'),

    path('blogs/<int:blog_pk>/comment/', 
        views.CommentCreateView.as_view(), name='comment_create'),
    
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    path('', RedirectView.as_view(pattern_name='blog_list', permanent=False)),
    ]
