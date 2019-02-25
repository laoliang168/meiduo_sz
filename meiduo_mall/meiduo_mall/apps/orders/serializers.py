from django.utils import timezone
from rest_framework import serializers
from django_redis import get_redis_connection
from decimal import Decimal
from django.db import transaction

from goods.models import SKU
from goods.serializers import SKUSerializer
from .models import OrderInfo, OrderGoods



class CommitOrderSerializer(serializers.ModelSerializer):
    """保存订单序列化器"""

    class Meta:
        model = OrderInfo
        fields = ['order_id', 'pay_method', 'address']
        # order_id 只做输出, pay_method/address只做输入
        read_only_fields = ['order_id']
        extra_kwargs = {
            'address': {
                'write_only': True,
                'required': True,
            },
            'pay_method': {
                'write_only': True,
                'required': True
            }
        }

    def create(self, validated_data):
        """重写序列化器的create方法进行存储订单表/订单商品"""
        # 订单基本信息表 订单商品表  sku   spu 四个表要么一起成功 要么一起失败

        # 获取当前保存订单时需要的信息
        # 获取user对象
        user = self.context['request'].user

        # 生成订单编号 当前时间 + user_id  20190215100800000000001
        order_id = timezone.now().strftime('%Y%m%d%H%M%S') + "%09d" % user.id
        # 获取用户选择的收货地址
        address = validated_data.get('address')
        # 获取支付方式
        pay_method = validated_data.get('pay_method')

        # 订单状态：如果用户选择的是货到付款，订单应该是待发货 如果用户选择支付方式是支付宝，订单应该是待支付
        # status = '待支付' if如果用户选择的方式是 == 支付宝支付 else ’待发货‘
        status = (
            OrderInfo.ORDER_STATUS_ENUM['UNPAID']
            if OrderInfo.PAY_METHODS_ENUM['ALIPAY'] == pay_method
            else OrderInfo.ORDER_STATUS_ENUM['UNSEND']
        )

        # 开启一个事务
        with transaction.atomic():
            # 创建事务保存点
            save_point = transaction.savepoint()
            try:
                # 保存订单基本信息 OrderInfo (外键'一'的一方)
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=0,
                    total_amount=Decimal('0.00'),
                    freight=Decimal('10.00'),
                    pay_method=pay_method,
                    status=status
                )
                # 从redis读取购物车中被勾选的商品信息
                redis_conn = get_redis_connection('cart')
                # {b'16:1',b'1:1'}
                cart_redis_dict = redis_conn.hgetall('cart_%d' % user.id)
                # {b'16}
                cart_selected_ids = redis_conn.smembers('selected_%d' % user.id)
                # 把要购买的商品id和count重新包到一个字典
                cart_selected_dict = {}  # {16:6}
                for sku_id_bytes in cart_selected_ids:
                    cart_selected_dict[int(sku_id_bytes)] = int(cart_redis_dict[sku_id_bytes])

                # skus = SKU.objects.filter(id__in cart_selected_dict.keys())  # 此处不需要一下子取出，因为并发时会有缓存问题

                # 每次单个取出sku对象
                for sku_id in cart_selected_dict:
                    while True:
                        # 获取sku对象
                        sku = SKU.objects.get(id=sku_id)
                        # 获取当前sku_id商品要购买的的数量
                        sku_count = cart_selected_dict[sku_id]

                        # 获取查询出sku那一刻库存和销量
                        origin_stock = sku.stock
                        origin_sales = sku.sales

                        # 判断库存
                        if sku_count > origin_stock:
                            raise serializers.ValidationError('库存不足')

                        # 计算新库存和销量
                        new_stock = origin_stock - sku_count
                        new_sales = origin_sales - sku_count

                        # 减少库存，增加销量 SKU   乐观锁
                        result = SKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock,
                                                                                          sales=new_sales)

                        if result == 0:
                            continue  # 跳出本次循环，进入下一次尝试，直到购买成功或者库存不足

                        # 修改spu销量
                        spu = sku.goods
                        spu.sales += sku_count
                        spu.save()

                        # 保存订单商品信息OrderGoods(订单外键多的一方)
                        OrderGoods.objects.create(
                            order=order,
                            sku=sku,
                            count=sku_count,
                            price=sku.price
                        )

                        # 累加计算总数量和总价
                        order.total_count +=sku_count
                        # 16(16号商品)  100*2      1    200*2
                        order.total_amount = order.total_amount + (sku.price * sku_count)

                        break  # 成功后跳出无限循环，继续对下一个sku_id进行下单


                # 最后加入邮费和保存订单信息（只加一次运费）
                order.total_amount += order.freight
                order.save()

            except Exception:
                # 暴力回滚，无论中间出现什么问题全部回滚
                transaction.savepoint_rollback(save_point)
                raise  # 将异常抛出
            else:
                transaction.savepoint_commit(save_point)  # 中间如果没有出现异常提交事件


        # 清除购物车中已结算的商品
        pl = redis_conn.pipeline()
        pl.hdel('cart_%d'% user.id, *cart_selected_ids)
        pl.srem('selected_%d'% user.id, *cart_selected_ids)
        pl.execute()

        # 返回订单
        return order

class CartSKUSerializer(serializers.ModelSerializer):
    """
    购物车商品数据序列化器
    """
    count = serializers.IntegerField(label='数量')

    class Meta:
        model = SKU
        fields = ('id', 'name', 'default_image_url', 'price', 'count')

class OrderSettlementSerializer(serializers.Serializer):
    """
    订单结算数据序列化器data
    """
    # max_digits 一共多少位；decimal_places：小数点保留几位
    freight = serializers.DecimalField(label='运费', max_digits=10, decimal_places=2)
    skus = CartSKUSerializer(many=True)


class SKUCommentSerializer(serializers.ModelSerializer):
    """商品评论序展示列化器"""
    sku = SKUSerializer()
    class Meta:
        model = OrderGoods
        fields = ['sku', 'price']


class CommentSerializer(serializers.ModelSerializer):
    """商品评论提交序列化器"""
    class Meta:
        model = OrderGoods
        fields = ['score','order','sku','comment','is_anonymous']

