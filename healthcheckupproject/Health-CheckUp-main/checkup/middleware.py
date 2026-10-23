from django.shortcuts import redirect
from django.conf import settings

class LoginRequiredMiddleware:
    """
    Middleware that ensures only logged-in users have access to the website.
    Unauthenticated users are redirected to the login page.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_urls = [
            '/login/',
            '/register/',
            '/logout/',
            '/auth/login/',
            '/auth/register/',
            '/auth/logout/',
        ]

    def __call__(self, request):
        path = request.path_info

        # Allow static and media files
        if path.startswith(settings.STATIC_URL) or (settings.MEDIA_URL and path.startswith(settings.MEDIA_URL)):
            return self.get_response(request)

        # Allow admin URLs (Django admin handles its own authentication)
        if path.startswith('/admin/'):
            return self.get_response(request)

        # Allow explicitly exempt auth paths
        is_exempt = any(path == url or path == url.rstrip('/') for url in self.exempt_urls)

        if not request.user.is_authenticated:
            if not is_exempt:
                login_url = getattr(settings, 'LOGIN_URL', '/login/')
                return redirect(f"{login_url}?next={request.get_full_path()}")
        else:
            # If already logged in and trying to visit login or register, redirect to home
            if path in ['/login/', '/login', '/register/', '/register', '/auth/login/', '/auth/login', '/auth/register/', '/auth/register']:
                return redirect('/')

        return self.get_response(request)
