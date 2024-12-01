# portfolio/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.portfolio_view, name='portfolio_view'),
    path('politique-de-confidentialite/', views.privacy_policy, name='privacy_policy'),
]
