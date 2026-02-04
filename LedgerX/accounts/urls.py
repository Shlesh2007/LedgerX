from .views import create_admin
from django.urls import path
from . import views

urlpatterns = [
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path("create-admin/", create_admin),
    # Registration Flow
    path('register/', views.register_view, name='register'),
    path('register/verify/', views.verify_registration_otp_view, name='verify_registration_otp'),

    # 3-Step Password Reset Flow
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('reset-new-password/', views.reset_password_confirm_view, name='reset_password_confirm'),

    path('logout/', views.logout_view, name='logout'),

    # Account / Shop management
    path('account/settings/', views.account_settings, name='account_settings'),
    
    # 🔴 SECURE DELETION FLOW (Updated to match views.py)
    path('account/delete/request/', views.delete_shop_request_view, name='delete_shop_request'),
    path('account/delete/verify/', views.delete_shop_verify_view, name='delete_shop_verify'),


    # ⚡ NEW AJAX URL
    path('api/check-username/', views.check_username, name='check_username'),
]
