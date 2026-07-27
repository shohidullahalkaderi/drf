from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """Strict Auth Throttle: 5 requests per minute per IP + target email."""
    scope = 'login'
    rate = '5/minute'

    def get_cache_key(self, request, view):
        email = (request.data.get('email') or '').strip().lower()
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': f"{ident}_{email}"
        }


class RegisterRateThrottle(SimpleRateThrottle):
    """Registration Throttle: 10 requests per minute per IP + target email."""
    scope = 'register'
    rate = '10/minute'

    def get_cache_key(self, request, view):
        email = (request.data.get('email') or '').strip().lower()
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': f"{ident}_{email}"
        }


class LogoutRateThrottle(SimpleRateThrottle):
    """Logout Throttle: 10 requests per minute per Token/IP (runs before auth)."""
    scope = 'logout'
    rate = '10/minute'

    def get_cache_key(self, request, view):
        # Extract Bearer token from header without triggering full authentication
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token_key = auth_header.split(' ')[1].strip()
            ident = token_key
        else:
            ident = self.get_ident(request)  # Fallback to IP address

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }