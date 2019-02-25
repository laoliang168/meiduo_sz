from django.shortcuts import render
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import CacheResponseMixin

from .models import Area
from .serializers import AreaSerializer,SubsAreaSerializer

# Create your views here.

class AreasViewSet(ReadOnlyModelViewSet,CacheResponseMixin):
    pagination_class = None

    def get_queryset(self):
        if self.action == 'list':
            return Area.objects.filter(parent_id = None)
        else:
            return Area.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return AreaSerializer
        else:
            return SubsAreaSerializer

