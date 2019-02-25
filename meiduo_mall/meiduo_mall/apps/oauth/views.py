from django.http import HttpResponse
from django.shortcuts import render
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django_redis import get_redis_connection
from random import randint

from QQLoginTool.QQtool import OAuthQQ
from rest_framework_jwt.settings import api_settings

from meiduo_mall.utils.captcha.captcha import captcha
from .models import QQAuthUser, OAuthSinaUser
from .utils import generate_save_user_token
from .serializers import QQAuthUserSerializer,WeiboAuthUserSerializer
from carts.utils import merge_cart_cookie_to_redis
from meiduo_mall.utils.oauthsinatool import OAuthWeibo
from celery_tasks.sms.tasks import send_sms_code
from . import constants

# Create your views here.
logger = logging.getLogger('django')


class QQAuthUserView(APIView):
    def get(self, request):
        code = request.query_params.get('code')
        if not code:
            return Response({'message': '缺少code'}, status=status.HTTP_400_BAD_REQUEST)

        oauthqq = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                          redirect_uri=settings.QQ_REDIRECT_URI,
                          state=next)
        try:
            access_token = oauthqq.get_access_token(code)
            openid = oauthqq.get_open_id(access_token)
        except Exception as e:
            logger.info(e)
            return Response({'message': 'QQ服务器异常'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 查找是否已绑定openid
        try:
            qqauth_model = QQAuthUser.objects.get(openid=openid)
        except QQAuthUser.DoesNotExist:
            openid_sin = generate_save_user_token(openid)  # 加密返回前段保存
            return Response({'access_token': openid_sin})
        else:
            # 手动生成token
            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER  # 加载生成载荷函数
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER  # 加载生成token函数
            # 获取user对象
            user = qqauth_model.user
            payload = jwt_payload_handler(user)  # 生成载荷
            token = jwt_encode_handler(payload)  # 根据载荷生成token
            response = Response({
                'token': token,
                'username': user.username,
                'user_id': user.id
            })

            # 做cookie购物车合并到redis操作
            merge_cart_cookie_to_redis(request, user, response)

            return response

    def post(self, request):

        serializer = QQAuthUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()  # 获取user对象

        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER  # 加载生成载荷函数
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER  # 加载生成token函数

        payload = jwt_payload_handler(user)  # 生成载荷
        token = jwt_encode_handler(payload)  # 根据载荷生成token

        response = Response({
            'token': token,
            'username': user.username,
            'user_id': user.id
        })

        # 做cookie购物车合并到redis操作
        merge_cart_cookie_to_redis(request, user, response)

        return response


class QQAuthURLView(APIView):

    def get(self, request):
        next = request.query_params.get('next')

        if not next:
            next = '/'

        oauthqq = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                          redirect_uri=settings.QQ_REDIRECT_URI,
                          state=next)

        login_url = oauthqq.get_qq_url()

        return Response({'login_url': login_url})


class OAuthWeiboURLView(APIView):
    """
    获取微博URL
    """

    def get(self, request):
        next = request.query_params.get('next')

        if not next:
            next = '/'

        oauthweibo = OAuthWeibo(client_id=settings.WEIBO_CILENT_ID, redirect_uri=settings.WEIBO_REDIRECT_URI,
                                state=next)

        login_url = oauthweibo.get_url()

        return Response({'login_url': login_url})

class ImageCodeView(APIView):
    """
    获取图片验证码
    """
    def get(self, request, image_code_id):

        # 3.1 生成验证码图片，验证码图片的真实值
        image_name, real_image_code, image_data = captcha.generate_captcha()
        redis_conn = get_redis_connection('verify_codes')

        # 3.2 image_code_id作为key将验证码图片的真实值保存到redis数据库，并且设置有效时长(5分钟)
        try:
            redis_conn.setex("CODEID_%s" % image_code_id, constants.SMS_CODE_REDIS_EXPIRES, real_image_code)
        except Exception as e:
            return Response({'message':'数据异常'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 4.1 返回验证码图片(返回的数据是二进制格式，不能兼容所有浏览器)

        return HttpResponse(image_data)

class WeiboSMSCodeView(APIView):
    """
    获取短信验证码
    """
    def get(self, request, mobile):
        # 串讲redis连接对象
        redis_conn = get_redis_connection('verify_codes')
        # 获取手机是否有发送过标志
        flag = redis_conn.get('send_flag_%s' % mobile)

        if flag:
            return Response(data={"message": "不能频繁发送短信"}, status=status.HTTP_400_BAD_REQUEST)

        # text = ' + this.image_code+' & image_code_id = '+ this.image_code_id
        image_code = request.query_params.get('text')
        image_code_id = request.query_params.get('image_code_id')

        real_code = redis_conn.get('CODEID_%s'% image_code_id).decode()
        if image_code.upper() != real_code.upper():
            return Response({'message':'参数错误'},status=status.HTTP_400_BAD_REQUEST)

        sms_code = '%06d' % randint(0, 999999)

        """保存验证码跟标志信息到redis数据库"""
        pl = redis_conn.pipeline()
        pl.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex('send_flag_%s' % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)
        pl.execute()

        # 使用celery调用云通讯发短信
        send_sms_code.delay(mobile, sms_code)  # 必须要delay异步执行，不然白搞celery了
        return Response({"message": "ok"})

class WeiboAuthUserView(APIView):
    """
    获取access_token,微博绑定用户视图
    """

    # 获取access_token,判断用户是否绑定，绑定返回用户数据，未绑定返回access_token
    def get(self, request):
        code = request.query_params.get('code')
        oauthweibo = OAuthWeibo(client_id=settings.WEIBO_CILENT_ID,
                                redirect_uri=settings.WEIBO_REDIRECT_URI,
                                client_secret=settings.WEIBO_CLIENT_SECRET, grant_type='authorization_code')
        try:
            access_token = oauthweibo.get_access_token(code=code)
        except:
            return Response({'message': 'access_token获取失败'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 保存accesstoken
        redis_conn = get_redis_connection('verify_codes')
        redis_conn.setex('access_token_%s'% code, constants.SMS_CODE_REDIS_EXPIRES, access_token)

        try:
            user_sina = OAuthSinaUser.objects.filter(access_token=access_token).first()
        except Exception as e:
            return Response({'message': '数据库异常'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not user_sina:
            # 先加密，后返回
            access_token_list = generate_save_user_token(access_token)
            return Response({'access_token': access_token_list})

        user = user_sina.user

        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER  # 加载生成载荷函数
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER  # 加载生成token函数

        payload = jwt_payload_handler(user)  # 生成载荷
        token = jwt_encode_handler(payload)  # 根据载荷生成token

        response = Response({
            'user_id': user.id,
            'username': user.username,
            'token': token
        })

        # 做cookie购物车合并到redis操作
        merge_cart_cookie_to_redis(request, user, response)

        return response


    def post(self, request):
        serializer = WeiboAuthUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()  # 获取user对象

        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER  # 加载生成载荷函数
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER  # 加载生成token函数

        payload = jwt_payload_handler(user)  # 生成载荷
        token = jwt_encode_handler(payload)  # 根据载荷生成token

        response = Response({
            'token': token,
            'username': user.username,
            'user_id': user.id
        })

        # 做cookie购物车合并到redis操作
        merge_cart_cookie_to_redis(request, user, response)

        return response




