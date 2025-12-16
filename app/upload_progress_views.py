"""
Views for tracking upload progress
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache


class UploadProgressView(APIView):
    """
    GET: Get upload progress by task_id
    """
    def get(self, request, task_id):
        try:
            progress_key = f'upload_progress_{task_id}'
            progress_data = cache.get(progress_key)
            
            # Debug: Log cache key and result
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Progress check - Key: {progress_key}, Found: {progress_data is not None}")
            
            if not progress_data:
                # Return a more helpful error message
                return Response(
                    {
                        'error': 'Upload progress not found. The task may have expired or never started.',
                        'task_id': task_id,
                        'cache_key': progress_key,
                        'hint': 'Make sure Redis is running and accessible to both Django and Celery worker'
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(progress_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            return Response(
                {
                    'error': f'Failed to get progress: {str(e)}',
                    'traceback': traceback.format_exc()
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

