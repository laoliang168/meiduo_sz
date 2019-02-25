import base64
import random

from django.contrib.auth.hashers import make_password
from django.shortcuts import render
import re
from rest_framework import status
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView, ListAPIView, GenericAPIView
from rest_framework.utils import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveAPIView, UpdateAPIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from django_redis import get_redis_connection
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.views import ObtainJSONWebToken

from .serializers import UserSerializer, UserDetailSerializer, EmailSerializer, UserAddressSerializer, \
    AddressTitleSerializer, UserBrowseHistorySerializer

from .models import User, Address
from goods.models import SKU
from goods.serializers import SKUSerializer
from carts.utils import merge_cart_cookie_to_redis
from meiduo_mall.utils.captcha.captcha import captcha
from . import constants
from celery_tasks.sms.tasks import send_sms_code


# Create your views here.
class UserAuthorizeView(ObtainJSONWebToken):
    """重写账号密码登录视图"""

    def post(self, request, *args, **kwargs):
        response = super(UserAuthorizeView, self).post(request, *args, **kwargs)
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.object.get('user') or request.user
            merge_cart_cookie_to_redis(request, user, response)
        return response


# POST/GET  /browse_histories/
class UserBrowseHistoryView(CreateAPIView):
    """用户浏览记录"""

    # 指定序列化器(校验)
    serializer_class = UserBrowseHistorySerializer
    # 指定权限
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """读取用户浏览记录"""
        # 创建redis连接对象
        redis_conn = get_redis_connection('history')
        # 查询出redis中当前登录用户的浏览记录[b'1', b'2', b'3']
        sku_ids = redis_conn.lrange('history_%d' % request.user.id, 0, -1)

        # 把sku_id对应的sku模型取出来
        # skus = SKU.objects.filter(id__in=sku_ids)  # 此查询它会对数据进行排序处理
        # 查询sku列表数据
        sku_list = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id)
            sku_list.append(sku)

        # 序列化器
        serializer = SKUSerializer(sku_list, many=True)

        return Response(serializer.data)


class AddressViewSet(UpdateModelMixin, CreateModelMixin, GenericViewSet):
    """用户收货地址"""
    permission_classes = [IsAuthenticated]

    serializer_class = UserAddressSerializer

    def create(self, request, *args, **kwargs):
        """新增收货地址"""
        # 判断用户的收货地址数量是否上限
        # address_count = Address.objects.filter(user=request.user).count()
        address_count = request.user.addresses.count()
        if address_count > 20:
            return Response({'message': '收货地址数量上限'}, status=status.HTTP_400_BAD_REQUEST)
        # # 创建序列化器给data参数传值(反序列化)
        #         # serializer = UserAddressSerializer(data=request.data, context={'request': request})
        #         # # 调用序列化器的is_valid方法
        #         # serializer.is_valid(raise_exception=True)
        #         # # 调用序列化器的save
        #         # serializer.save()
        #         # # 响应
        #         # return Response(serializer.data, status=status.HTTP_201_CREATED)
        return super(AddressViewSet, self).create(request, *args, **kwargs)

    def get_queryset(self):
        return self.request.user.addresses.filter(is_deleted=False)

    # GET /addresses/
    def list(self, request, *args, **kwargs):
        """
        用户地址列表数据
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        user = self.request.user
        return Response({
            'user_id': user.id,
            'default_address_id': user.default_address_id,
            'limit': 20,
            'addresses': serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        """
        处理删除
        """
        address = self.get_object()

        # 进行逻辑删除
        address.is_deleted = True
        address.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    # put /addresses/pk/status/
    @action(methods=['put'], detail=True)
    def status(self, request, pk=None):
        """
        设置默认地址
        """
        address = self.get_object()
        request.user.default_address = address
        request.user.save()
        return Response({'message': 'OK'}, status=status.HTTP_200_OK)

    # put /addresses/pk/title/
    # 需要请求体参数 title
    @action(methods=['put'], detail=True)
    def title(self, request, pk=None):
        """
        修改标题
        """
        address = self.get_object()
        serializer = AddressTitleSerializer(instance=address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class EmailVerifyView(APIView):
    """激活邮箱"""

    def get(self, request):

        # 1.获取前token查询参数
        token = request.query_params.get('token')
        if not token:
            return Response({'message': '缺少token'}, status=status.HTTP_400_BAD_REQUEST)

        # 对token解密并返回查询到的user
        user = User.check_verify_email_token(token)

        if not user:
            return Response({'message': '无效token'}, status=status.HTTP_400_BAD_REQUEST)

        # 修改user的email_active字段
        user.email_active = True
        user.save()

        return Response({'message': 'ok'})


# PUT  /email/
class EmailView(UpdateAPIView):
    """保存邮箱"""
    permission_classes = [IsAuthenticated]
    # 指定序列化器
    serializer_class = EmailSerializer

    def get_object(self):
        return self.request.user


"""
# GET   /user/
class UserDetailView(APIView):
    # 提供用户个人信息接口
    # 指定权限,必须是通过认证的用户才能访问此接口(就是当前本网站的登录用户)
    permission_classes = [IsAuthenticated] 

    def get(self, request):
        user = request.user  # 获取本次请求的用户对象
        serializer = UserDetailSerializer(user)
        return Response(serializer.data)
"""


class UserDetailView(RetrieveAPIView):
    """提供用户个人信息接口"""
    permission_classes = [IsAuthenticated]  # 指定权限,必须是通过认证的用户才能访问此接口(就是当前本网站的登录用户)

    serializer_class = UserDetailSerializer  # 指定序列化器

    # queryset = User.objects.all()
    def get_object(self):  # 返回指定模型对象
        return self.request.user


# POST /users/
class UserView(CreateAPIView):
    """用户注册"""
    # 指定序列化器
    serializer_class = UserSerializer

# url(r'^usernames/(?P<username>\w{5,20})/count/$', views.UsernameCountView.as_view()),
class UsernameCountView(APIView):
    """验证用户名是否已存在"""

    def get(self, request, username):
        # 查询用户名是否已存在
        count = User.objects.filter(username=username).count()

        # 构建响应数据
        data = {
            'count': count,
            'username': username
        }
        return Response(data)


# url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
class MobileCountView(APIView):
    """验证手机号是否已存在"""

    def get(self, request, mobile):
        # 查询手机号数量
        count = User.objects.filter(mobile=mobile).count()

        data = {
            'count': count,
            'mobile': mobile
        }
        return Response(data)


class UpdataPasswordView(APIView):
    """
    用户修改密码
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, user_id):

        old_password = request.data.get('old_password')
        newpassword1 = request.data.get('password')
        newpassword2 = request.data.get('password2')
        if newpassword1 != newpassword2:
            return Response({'message': '密码不一致'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'message': '用户不存在'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(old_password):
            return Response({'message': '密码不正确'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user.set_password(newpassword1)
            user.save()
        except Exception as e:
            return Response({'message': '数据库异常'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({'message': 'OK'})



class ImageCode(APIView):
    def get(self, request):
        img_url = request.get_full_path()
        image_code = re.search('image_codes/([0-9a-zA-Z\-]+)', img_url)
        # 匹配括号中的url
        image_code_id = image_code.group(1)

        # 生成验证码
        name, text, img = captcha.generate_captcha()
        # 只要保存验证码值和uuid
        redis_conn = get_redis_connection('verify_codes')
        pl = redis_conn.pipeline()
        # 设置时长
        redis_conn.setex('img_codes_%s' % image_code_id, 60, text)
        pl.execute()

        return HttpResponse(img, content_type='image/jpg')


class FindPassSMSCodeView(APIView):
    # 发送短信
    def get(self, request):

        try:
            access_token = request.query_params.get('access_token')
            payld = access_token.split('.')
            data_str = payld[1]
            data_dict = eval(base64.b64decode(data_str))
            user_id = data_dict['user_id']

            user = User.objects.get(id=user_id)
            mobile = user.mobile

            redis_conn = get_redis_connection('verify_codes')

            #  1.判断用户在60秒内是否重发短信
            send_flag = redis_conn.get('send_flag_%s' % mobile)
            # 2.如果已发送就提前响应，不执行后续代码

            if send_flag:
                return Response({"message": "不可频繁发送短信"}, status=status.HTTP_400_BAD_REQUEST)

            # 3.生成短信验证码
            sms_code = '%06d' % random.randint(0, 999999)
            print(sms_code)
            pl = redis_conn.pipeline()

            pl.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)

            # 4.2保存发送短信验证码标记
            pl.setex('send_flag_%s' % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)
            pl.execute()

            # 5.使用云通讯发送验证码
            # 用异步发送短信,触发异步任务
            send_sms_code.delay(mobile, sms_code)

            # 6.响应
            data = {
                'token': access_token
            }
            return Response(data=data)
        except:
            data = {}
            return Response(data=data, status=status.HTTP_404_NOT_FOUND)


class VerifyNemasView(APIView):
    """
    验证用户名是否存在
    """

    def get(self, request, username):
        #  提取url中的参数
        username = username
        text = request.query_params.get('text')
        image_code_id = request.query_params.get('image_code_id')

        try:
            # first() 获取user对象实例
            user = User.objects.filter(username=username).first()
            # 根据username 查找mobile
            user_mobile = user.mobile
            # # 连接redis
            redis_conn = get_redis_connection('verify_codes')
            # 取出 uuid对应的验证码（此处未测试是否会过期）
            texts = redis_conn.get('img_codes_%s' % image_code_id)
            # 换成大写比较
            if text.upper() == texts.decode().upper():
                secret_mobile = user_mobile[:3] + "****" + user_mobile[7:]

                jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER  # 加载生成载荷函数
                jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER  # 加载生成token函数

                # 获取user对象
                payload = jwt_payload_handler(user)  # 生成载荷
                token = jwt_encode_handler(payload)  # 根据载荷生成token

                response = Response({
                    'access_token': token,
                    'user_id': user.id,
                    'mobile': secret_mobile,
                })
                # redis_conn.setex('access_token_%s' %'ACCESS_TOKEN',180,user_mobile)
                return response
            else:
                return Response({'message': '验证码错误'}, status=status.HTTP_400_BAD_REQUEST)

        except:
            data = {}
            return Response(data=data, status=status.HTTP_404_NOT_FOUND)


class VerifyMobileView(APIView):
    # 校验短信验证码
    def get(self, request, username):

        try:
            username = username
            sms_code = request.query_params.get('sms_code')

            user = User.objects.filter(username=username).first()
            mobile = user.mobile
            # # 连接redis
            redis_conn = get_redis_connection('verify_codes')
            # 取出短信验证码
            sms_text = redis_conn.get('sms_%s' % mobile)

            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER  # 加载生成载荷函数
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER  # 加载生成token函数

            # 获取user对象
            payload = jwt_payload_handler(user)  # 生成载荷
            token = jwt_encode_handler(payload)  # 根据载荷生成token

            if sms_code == sms_text.decode():
                data = {
                    'user_id': user.id,
                    'access_token': token
                }
                return Response(data=data)

        except:
            data = {}
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)


class NewPassView(APIView):
    """实现重置密码"""

    def post(self, request, user_id):
        password = request.data.get("password")
        password2 = request.data.get("password2")
        access_token = request.data.get("access_token")

        if password != password2:
            return Response({'message': '两次密码输入不一致'}, status=status.HTTP_400_BAD_REQUEST)

        payld = access_token.split('.')
        data_str = payld[1]
        data_dict = eval(base64.b64decode(data_str))
        user_id = data_dict['user_id']

        user = User.objects.get(id=user_id)
        user.set_password(password)
        user.save()
        return Response({'message': 'ok'})
