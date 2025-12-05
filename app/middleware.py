"""
Custom middleware for adding cache headers to API responses
"""
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
import hashlib
import json

class CacheControlMiddleware(MiddlewareMixin):
    """
    Adds cache headers to API responses for better performance
    """
    
    # Cache duration in seconds
    CACHE_DURATION = {
        'GET': 5,  # 5 seconds for GET requests - allows quick data refresh after uploads
        'default': 5,  # 5 seconds for other requests
    }
    
    # Endpoints that should not be cached (for real-time data)
    NO_CACHE_PATHS = [
        '/api/v1/auth/',
        '/api/v1/users/me/',
        '/admin/',
        '/api/v1/trucking/clear/',
        '/api/v1/trucking/lock/',
        '/api/v1/trucking/upload/',  # Upload endpoints should not be cached
    ]
    
    def process_response(self, request, response):
        # Only add cache headers for successful API responses
        if not response.status_code == 200:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
        
        # Don't cache authentication endpoints or admin
        path = request.path
        if any(no_cache_path in path for no_cache_path in self.NO_CACHE_PATHS):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            return response
        
        # Add cache headers based on request method
        method = request.method
        cache_duration = self.CACHE_DURATION.get(method, self.CACHE_DURATION['default'])
        
        if method == 'GET':
            # Cache GET requests
            response['Cache-Control'] = f'public, max-age={cache_duration}, stale-while-revalidate=600'
            response['X-Cache-Status'] = 'enabled'
        else:
            # No cache for POST/PUT/PATCH/DELETE
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        # Add ETag support for better caching
        if method == 'GET' and hasattr(response, 'data'):
            try:
                content = json.dumps(response.data, sort_keys=True, default=str)
                etag = hashlib.md5(content.encode()).hexdigest()
                response['ETag'] = f'"{etag}"'
            except (TypeError, AttributeError):
                pass
        
        return response

