from django.contrib import admin
from blog_generator import views
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.login_view, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('signup/', views.user_signup, name='signup'),
    path('', include('blog_generator.urls'))
]

urlpatterns = urlpatterns+static(settings.MEDIA_URL, document_root= settings.MEDIA_ROOT)