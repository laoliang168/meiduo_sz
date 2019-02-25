from rest_framework import serializers
from drf_haystack.serializers import HaystackSerializer

from orders.models import OrderGoods, OrderInfo
from .models import SKU
from .search_indexes import SKUIndex
from users.models import User

class UserNameSerializer(serializers.ModelSerializer):
    """下单用户序列化器"""
    class Meta:
        model = User
        fields = ['username']


class OrderInfoUserSerializer(serializers.ModelSerializer):
    """订单用户序列化器"""
    user = UserNameSerializer()
    class Meta:
        model = OrderInfo
        fields =['user']


class CommentShowSerializer(serializers.ModelSerializer):
    """商品展示序列化器"""
    order = OrderInfoUserSerializer()
    class Meta:
        model = OrderGoods
        fields = ['comment', 'score', 'order', 'is_anonymous']


class SKUInfoSerializer(serializers.ModelSerializer):
    """订单商品详情"""
    class Meta:
        model = SKU
        fields = ['id', 'name', 'default_image_url']


class OrderGoodsSerializer(serializers.ModelSerializer):
    """订单商品数据序列化器"""
    sku = SKUInfoSerializer()

    class Meta:
        model = OrderGoods
        fields = ['count', 'sku', 'price']


class OrderInfoSerializer(serializers.ModelSerializer):
    """订单信息数据序列化器"""
    skus = OrderGoodsSerializer(many=True)

    class Meta:
        model = OrderInfo
        fields = ['status', 'pay_method', 'total_amount', 'freight', 'create_time', 'order_id', 'skus']


class SKUSerializer(serializers.ModelSerializer):
    """商品列表界面"""

    class Meta:
        model = SKU
        fields = ['id', 'name', 'price', 'default_image_url', 'comments']


class SKUIndexSerializer(HaystackSerializer):
    """
    SKU索引结果数据序列化器
    """
    object = SKUSerializer(read_only=True)

    class Meta:
        index_classes = [SKUIndex]
        fields = ('text', 'object')
