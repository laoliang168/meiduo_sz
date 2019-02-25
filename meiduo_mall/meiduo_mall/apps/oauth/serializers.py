from rest_framework import serializers
from django_redis import get_redis_connection

from .utils import check_save_user_token
from users.models import User
from .models import QQAuthUser, OAuthSinaUser

class QQAuthUserSerializer(serializers.Serializer):
    """绑定用户序列化器"""

    access_token = serializers.CharField(label='操作凭证',write_only=True)
    mobile = serializers.RegexField(label='手机号',regex=r'^1[3-9]\d{9}$',write_only=True)
    password = serializers.CharField(label='密码',max_length=20,min_length=8, write_only=True)
    sms_code = serializers.CharField(label='短信验证码',write_only=True)

    def validate(self, attrs):
        access_token = attrs.get('access_token')
        openid = check_save_user_token(access_token) # 获取解密后的openid
        if not openid:
            raise serializers.ValidationError('openid无效')
        attrs['access_token'] = openid  # 把解密后的openid 保存到反序列化的大字典中以备后期绑定用户时使用

        redis_conn = get_redis_connection('verify_codes')
        mobile = attrs.get('mobile')
        real_sms_code = redis_conn.get('sms_%s'% mobile).decode()
        sms_code = attrs.get('sms_code')
        if real_sms_code != sms_code:
            raise serializers.ValidationError('验证码错误')

        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            pass
        else:
            attrs['user']=user # 如果用户已注册,则给反序列化字典添加user属性
        return attrs

    def create(self, validated_data):
        """把openid和user进行绑定"""
        user = validated_data.get('user')
        if not user:
            user = User(
                username = validated_data.get('mobile'),
                password = validated_data.get('password'),
                mobile = validated_data.get('mobile'),
            )
            user.set_password(validated_data.get('password'))
            user.save()

        QQAuthUser.objects.create(
            user=user,
            openid = validated_data.get('access_token')
        )
        return user

class WeiboAuthUserSerializer(QQAuthUserSerializer):
    """
    绑定微博账号序列化器
    """
    code = serializers.CharField(label='获取access_token的令牌', write_only=True)
    access_token = serializers.CharField(label='操作凭证', write_only=True)
    mobile = serializers.RegexField(label='手机号', regex=r'^1[3-9]\d{9}$', write_only=True)
    password = serializers.CharField(label='密码', max_length=20, min_length=8, write_only=True)
    sms_code = serializers.CharField(label='短信验证码', write_only=True)

    def validate(self, attrs):
        access_token_hash = attrs.get('access_token')
        access_token = check_save_user_token(access_token_hash)  # 解密后校验
        code = attrs.get('code')
        redis_conn = get_redis_connection('verify_codes')
        real_access_token = redis_conn.get("access_token_%s"% code).decode()
        if real_access_token != access_token:
            raise serializers.ValidationError('access_token无效')

        mobile = attrs.get('mobile')
        real_sms_code = redis_conn.get('sms_%s' % mobile).decode()
        sms_code = attrs.get('sms_code')
        if real_sms_code != sms_code:
            raise serializers.ValidationError('验证码错误')

        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            pass
        else:
            attrs['user'] = user  # 如果用户已注册,则给反序列化字典添加user属性
        return attrs

    def create(self, validated_data):
        """把access_token和user进行绑定"""
        user = validated_data.get('user')
        if not user:
            user = User(
                username=validated_data.get('mobile'),
                password=validated_data.get('password'),
                mobile=validated_data.get('mobile'),
            )
            user.set_password(validated_data.get('password'))
            user.save()

        OAuthSinaUser.objects.create(
            user=user,
            access_token=validated_data.get('access_token')
        )
        return user
