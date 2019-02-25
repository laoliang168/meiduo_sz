from celery import Celery #导入异步任务类
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings.dev")

# 创建celery客户端
celery_app = Celery('meiduo')

# 加载配置信息
celery_app.config_from_object('celery_tasks.config')

# 注册异步任务（哪些任务可以进入到任务队列）
celery_app.autodiscover_tasks(['celery_tasks.sms','celery_tasks.email','celery_tasks.html'])

