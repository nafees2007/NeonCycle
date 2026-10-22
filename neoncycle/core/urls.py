from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_redirect, name='home'),
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('household/', views.household_dashboard, name='household_dashboard'),
    path('collector/', views.collector_dashboard, name='collector_dashboard'),
    path('recycler/', views.recycler_dashboard, name='recycler_dashboard'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('api/ai-forecast/', views.api_ai_forecast, name='api_ai_forecast'),
    path('api/live-ticker/', views.api_live_ticker, name='api_live_ticker'),
]