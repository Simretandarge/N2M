"""
Reader account URLs: /account/settings, /account/liked, /account/bookmarks, /account/preferences
Mount at path('account/', include(('accounts.reader_urls', 'reader'))) in config/urls.py
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.account_settings, name='account_settings'),
    path('liked/', views.account_liked_posts, name='account_liked_posts'),
    path('bookmarks/', views.account_bookmarks, name='account_bookmarks'),
    path('preferences/', views.account_preferences, name='account_preferences'),
]
