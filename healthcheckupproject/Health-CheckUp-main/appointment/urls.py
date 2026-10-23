from django.urls import path
from appointment import views 
from django.contrib.auth.decorators import login_required , permission_required  

urlpatterns = [
    path("register/", views.register_request, name="auth-register"),
    path("register", views.register_request),
    path("login/", views.login_request, name="auth-login"),
    path("login", views.login_request),
    path("book-appointment/", login_required(views.search), name="appointment"),
    path("book-appointment", login_required(views.search)),
    path("search-and-book-appointment/", views.BookAppointment.as_view(), name="search"),
    path("search-and-book-appointment", views.BookAppointment.as_view()),
    path("logout/", views.logout_request, name="auth-logout"),
    path("logout", views.logout_request),
]