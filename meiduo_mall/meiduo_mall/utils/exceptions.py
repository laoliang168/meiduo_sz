from django.db import DatabaseError
from rest_framework import status
from redis.exceptions import RedisError
from rest_framework.response import Response
import logging
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger('django')

def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        view = context['view']
        if isinstance(exc,DatabaseError) or isinstance(exc, RedisError):
            logger.error('[%s] %s'%(view, exc))
            response = Response({'message':'服务器内部错误'},status=status.HTTP_507_INSUFFICIENT_STORAGE)

    return response