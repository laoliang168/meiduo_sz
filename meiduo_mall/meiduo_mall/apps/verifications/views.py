from django.shortcuts import render
from rest_framework.views import APIView
from random import randint
from django_redis import get_redis_connection
from rest_framework.response import Response
import logging
from celery_tasks.sms.tasks import send_sms_code
from rest_framework import status

from . import constants

logger = logging.getLogger('django')
# url(r'^sms_codes/(?P<mobile>/$',views.SMSCodeView.as_view())
class SMSCodeView(APIView):

    def get(self,request,mobile):
        # 串讲redis连接对象
        redis_conn = get_redis_connection('verify_codes')
        # 获取手机是否有发送过标志
        flag = redis_conn.get('send_flag_%s'% mobile)

        # print(flag)
        if flag:
            return Response(data={"message":"不能频繁发送短信"}, status=status.HTTP_400_BAD_REQUEST)

        sms_code = '%06d'% randint(0,999999)
        logger.info(sms_code)

        """保存验证码跟标志信息到redis数据库"""
        pl = redis_conn.pipeline()
        pl.setex('sms_%s'% mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex('send_flag_%s'% mobile, constants.SEND_SMS_CODE_INTERVAL,1)
        pl.execute()

        # 使用celery调用云通讯发短信
        send_sms_code.delay(mobile,sms_code) # 必须要delay异步执行，不然白搞celery了
        return Response({"message":"ok"})