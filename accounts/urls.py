from django.urls import path
from . import views
from .views import auth_view, index_view, logout_view, my_account_view, edit_profile_view
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', auth_view, name='auth'),
    path('logout/', logout_view, name='logout'),
    path('index/', index_view, name='index'),
    path('myaccount/', my_account_view, name='myaccount'),
    path('edit_profile/', edit_profile_view, name='edit_profile'),
    path("toggle-show-email/", views.toggle_show_email, name="toggle_show_email"),
    path('update-privacy/', views.update_privacy_setting, name='update_privacy_setting'),
    path('settings/', views.settings_page_view, name='settings'),
    path('delete-account/', views.delete_account_view, name='delete_account'),

    path('settings/', views.settings_page_view, name='settings_page'),
    path('change-password/', views.custom_password_change, name='change_password'),
    path('change-password/', auth_views.PasswordChangeView.as_view(
        template_name='change_password.html',
        success_url='/accounts/change-password-done/'
    ), name='change_password'),

    path('change-password-done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='change_password_done.html'
    ), name='password_change_done'),
]
