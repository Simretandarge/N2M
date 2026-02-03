"""
URL routing for Next 251 Media content app.
"""
from django.urls import path
from . import views

app_name = 'content'

urlpatterns = [
    path('', views.home, name='home'),
    path('articles/', views.post_list, name='post_list'),
    path('articles/<slug:slug>/', views.post_detail, name='post_detail'),
    path('ai/', views.category_detail, kwargs={'slug': 'ai'}, name='category_ai'),
    path('startups/', views.category_detail, kwargs={'slug': 'startups'}, name='category_startups'),
    path('topic/<slug:slug>/', views.category_detail, name='category_detail'),
    path('reviews/', views.review_list, name='review_list'),
    path('reviews/<slug:slug>/', views.review_detail, name='review_detail'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('newsletter/', views.newsletter_signup, name='newsletter_signup'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    # Writer interface (no Django admin)
    path('writer/posts/', views.writer_post_list, name='writer_post_list'),
    path('writer/posts/new/', views.writer_post_create, name='writer_post_create'),
    path('writer/posts/<int:pk>/edit/', views.writer_post_edit, name='writer_post_edit'),
    path('writer/reviews/', views.writer_review_list, name='writer_review_list'),
    path('writer/reviews/new/', views.writer_review_create, name='writer_review_create'),
    path('writer/reviews/<int:pk>/edit/', views.writer_review_edit, name='writer_review_edit'),
]
