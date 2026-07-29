"""
URL configuration for Next 251 Media (N2M).
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.views.generic import RedirectView

from content.sitemaps import PostSitemap, ReviewSitemap, StaticSitemap

sitemaps = {
    'posts': PostSitemap,
    'reviews': ReviewSitemap,
    'static': StaticSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', RedirectView.as_view(pattern_name='accounts:login', permanent=False, query_string=True)),
    path('signup/', RedirectView.as_view(pattern_name='accounts:signup', permanent=False, query_string=True)),
    path('accounts/', include('accounts.urls')),
    path('account/', include(('accounts.reader_urls', 'reader'))),
    path('', include('content.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
