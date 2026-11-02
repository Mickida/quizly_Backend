from django.urls import path

from auth_app.api.views import (
    CookieTokenRefreshView,
    LoginView,
    LogoutView,
    RegistrationView,
)

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', CookieTokenRefreshView.as_view(),
         name='token_refresh'),
]
