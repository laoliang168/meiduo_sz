from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_redis import get_redis_connection
from decimal import Decimal
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView

from goods.models import SKU
from orders.models import OrderInfo, OrderGoods
from .serializers import CommitOrderSerializer, OrderSettlementSerializer, SKUCommentSerializer, CommentSerializer


# Create your views here.
class CommitOrderView(CreateAPIView):
    # 指定权限
    permission_classes = [IsAuthenticated]
    # 指定序列化器
    serializer_class = CommitOrderSerializer


class OrderSettlementView(APIView):
    """去结算接口"""

    # 给视图指定权限
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """获取"""
        user = request.user

        # 从购物车中获取用户勾选要结算的商品信息
        redis_conn = get_redis_connection('cart')
        redis_cart = redis_conn.hgetall('cart_%s' % user.id)
        cart_selected = redis_conn.smembers('selected_%s' % user.id)
        cart = {}

        for sku_id in cart_selected:
            cart[int(sku_id)] = int(redis_cart[sku_id])

        # 查询商品信息
        skus = SKU.objects.filter(id__in=cart.keys())
        for sku in skus:
            sku.count = cart[sku.id]

        # 运费
        freight = Decimal('10.00')
        # 创建序列化器时，给instance参数可以传递（模型/查询集（many=True）/字典）
        serializer = OrderSettlementSerializer({'freight': freight, 'skus': skus})

        return Response(serializer.data)


# get(this.host+'/orders/'+this.order_id+'/uncommentgoods/'
class CommentsView(APIView):
    """
    评论界面展示
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        # 获取用户
        user = request.user
        # 查询订单是否存在
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, status=OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT'])
        except OrderInfo.DoesNotExist:
            return Response({'message': '订单信息有误'}, status=status.HTTP_400_BAD_REQUEST)

        # 查询出订单的所有商品对象
        skugoods = order.skus.all()

        serializer = SKUCommentSerializer(skugoods, many=True)

        # # 返回
        return Response(serializer.data)


class CommentCommitView(APIView):
    """评论提交"""

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):

        user = request.user

        # 查询订单是否是本用户的
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, status=OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT'])
        except OrderInfo.DoesNotExist:
            return Response({'message': '订单信息有误'}, status=status.HTTP_400_BAD_REQUEST)

        # 1.拿到request.data参数
        data = request.data
        try:
            instance = OrderGoods.objects.get(order=order, sku_id=data.get('sku'))
        except OrderGoods.DoesNotExist:
            return Response({'message': '查无此订单商品'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. 检验参数，反序列化,partial=True 必传参数缺少时可用
        # 3.保存
        serializer = CommentSerializer(instance=instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        # 4，修改订单商品信息 is_commented

        instance.comment = serializer.validated_data.get('comment')
        instance.score = serializer.validated_data.get('score')
        instance.is_anonymous= serializer.validated_data.get('is_anonymous')
        instance.is_commented = True
        instance.save()

        # 5.修改订单状态
        skus = order.skus.all()
        for sku in skus:
            if not sku.is_commented:
                return Response(serializer.data)

        order.status = 5
        order.save()

        return Response(serializer.data)
