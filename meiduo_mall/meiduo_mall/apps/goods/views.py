from django.shortcuts import render
from rest_framework.generics import ListAPIView
from rest_framework.filters import OrderingFilter
from drf_haystack.viewsets import HaystackViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from orders.models import OrderInfo, OrderGoods
from .models import SKU
from .serializers import SKUSerializer, SKUIndexSerializer, OrderInfoSerializer, CommentShowSerializer


# Create your views here.


class UserInfoOrderView(ListAPIView):
    """个人订单"""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderInfoSerializer

    # queryset = OrderInfo.objects.all()

    def get_queryset(self):
        user = self.request.user
        orders = OrderInfo.objects.filter(user_id=user.id)
        for order in orders:
            order.create_time = order.create_time.strftime('%Y-%m-%d %H:%M:%S')
        return orders

    # pagination_class = PageNumberPagination


class SKUListView(ListAPIView):
    """商品列表界面"""

    serializer_class = SKUSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ['creat_time', 'price', 'sales']

    def get_queryset(self):
        category_id = self.kwargs.get('category_id')  # 获取url路径中的正则组别名提取出来的参数

        return SKU.objects.filter(is_launched=True, category_id=category_id)


class SKUSearchViewSet(HaystackViewSet):
    """
    SKU搜索
    """
    index_models = [SKU]

    serializer_class = SKUIndexSerializer


class CommentShowView(APIView):
    """
    商品评论展示
    """
    # 通过sku_id获取参数ordergoods 对象
    def get(self, request, sku_id):
        ordergoods = OrderGoods.objects.filter(sku_id=sku_id).all()
        serializer = CommentShowSerializer(ordergoods, many=True)
        data_list = serializer.data

        for item in data_list:
            item['username'] = item['order']['user']['username']
            del item['order']
            if item['is_anonymous']:
                item['username'] = item['username'][0:2] + '***' + item['username'][-1]

        return Response(data=data_list)
