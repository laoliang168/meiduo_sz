# 编辑异步任务代码

from celery_tasks.main import celery_app # 导入异步任务实例
from celery_tasks.sms.yuntongxun.sms import CCP # 导入云通讯类
from . import constants # 导入常量文件

@celery_app.task() # 用celery_app调用task方法装饰函数为异步任务
def send_sms_code(mobile, sms_code):
    CCP().send_template_sms(mobile,[sms_code,constants.SMS_CODE_REDIS_EXPIRES//60],1)