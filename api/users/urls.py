from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    SignupView,
    VerifyEmailView,
    LoginView,
    SwitchWorkspaceView,
    UserProfileView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path('auth/signup/', SignupView.as_view(), name='auth-signup'),
    path('auth/verify/', VerifyEmailView.as_view(), name='auth-verify'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('auth/switch-workspace/', SwitchWorkspaceView.as_view(), name='auth-switch-workspace'),
    path('auth/password-reset-request/', PasswordResetRequestView.as_view(), name='auth-password-reset-request'),
    path('auth/password-reset-confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),
    path('users/profile/', UserProfileView.as_view(), name='users-profile'),
]
