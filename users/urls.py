from django.urls import path

from . import views


app_name = 'users'

urlpatterns = [
    path('list/', views.user_list, name='user_list'),
    path('<int:user_id>/', views.user_detail, name='user_detail'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('<int:user_id>/edit/', views.edit_profile, name='edit_profile'),
    path('edit/', views.edit_my_profile, name='edit_my_profile'),
    path('change-password/', views.change_password, name='change_password'),
]