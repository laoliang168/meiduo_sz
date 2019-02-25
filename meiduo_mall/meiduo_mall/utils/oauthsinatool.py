from django.conf import settings
from urllib.parse import urlencode, parse_qs
import json
import requests


class OAuthWeibo(object):
    """
    微博登录SDK
    """
    def __init__(self, client_id=None, redirect_uri=None, state=None,client_secret=None,grant_type=None):
        self.client_id = client_id
        self.redirect_uri = redirect_uri # 用于保存登录成功后的跳转页面路径
        self.state = state
        self.client_secret = client_secret
        self.grant_type=grant_type

    # https: // api.weibo.com / oauth2 / authorize?client_id = 123050457758183 & redirect_uri = http: // www.example.com / response & response_type = code
    def get_url(self):
        # Weibo登录url参数组建
        data_dict = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'state': self.state
        }

        # 构建url
        weibo_url = 'https://api.weibo.com/oauth2/authorize?' + urlencode(data_dict)

        return weibo_url

    def get_access_token(self, code):
        # 构建参数数据
        data_dict = {
            'grant_type': self.grant_type,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'code': code
        }

        # 构建url
        access_url = 'https://api.weibo.com/oauth2/access_token?'

        # 发送请求
        try:
            response = requests.post(access_url, data_dict)

            # 提取数据
            data = response.text
            data_dict = json.loads(data)
        except:
            raise Exception('weibo请求失败')

        # 提取access_token
        access_token = data_dict.get('access_token', None)

        if not access_token:
            raise Exception('access_token获取失败')

        return access_token
