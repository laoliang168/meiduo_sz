from django.db import models
from django.contrib.auth.models import AbstractUser
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
from django.conf import settings

# Create your models here.
from meiduo_mall.utils.models import BaseModel


class User(AbstractUser):
    default_address = models.ForeignKey('Address', related_name='users', null=True, blank=True,
                                        on_delete=models.SET_NULL, verbose_name='默认地址')
    mobile = models.CharField(max_length=11, unique=True, verbose_name='手机号')
    email_active = models.BooleanField(default=False,verbose_name='邮箱激活状态')
    class Meta:
        db_table = 'tb_users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def generate_verify_email_url(self):
        """生成激活URL"""
        serializer = Serializer(settings.SECRET_KEY, 24*60*60)
        data = {
            'user_id':self.id,
            'email':self.email
        }
        token = serializer.dumps(data).decode()

        return 'http://www.meiduo.site:8080/success_verify_email.html?token=' + token


    @staticmethod
    def cheeck_verify_email_token(token):
        serializer = Serializer(settings.SECRET_KEY, 24*60*60)
        try:
            data = serializer.loads(token)
        except BadData:
            return None
        else:
            user_id = data.get('user_id')
            email = data.get('email')
            try:
                user = User.objects.get(id=user_id,email=email)
            except User.DoesNotExist:
                return None
            else:
                return user

class Address(BaseModel):
    """
    用户地址
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses', verbose_name='用户')
    title = models.CharField(max_length=20, verbose_name='地址名称')
    receiver = models.CharField(max_length=20, verbose_name='收货人')
    province = models.ForeignKey('areas.Area', on_delete=models.PROTECT, related_name='province_addresses', verbose_name='省')
    city = models.ForeignKey('areas.Area', on_delete=models.PROTECT, related_name='city_addresses', verbose_name='市')
    district = models.ForeignKey('areas.Area', on_delete=models.PROTECT, related_name='district_addresses', verbose_name='区')
    place = models.CharField(max_length=50, verbose_name='地址')
    mobile = models.CharField(max_length=11, verbose_name='手机')
    tel = models.CharField(max_length=20, null=True, blank=True, default='', verbose_name='固定电话')
    email = models.CharField(max_length=30, null=True, blank=True, default='', verbose_name='电子邮箱')
    is_deleted = models.BooleanField(default=False, verbose_name='逻辑删除')

    class Meta:
        db_table = 'tb_address'
        verbose_name = '用户地址'
        verbose_name_plural = verbose_name
        ordering = ['-update_time']