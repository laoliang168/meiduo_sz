from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^qq/authorization/$', views.QQAuthURLView.as_view()),
    url(r'^qq/user/$', views.QQAuthUserView.as_view()),
    url(r'^weibo/authorization/$',views.OAuthWeiboURLView.as_view()),
    url(r'^sina/user/$', views.WeiboAuthUserView.as_view()),
    url(r'^image_codes/(?P<image_code_id>\w{8}(-\w{4}){3}-\w{12})/$',views.ImageCodeView.as_view()),
    url(r'^sms_codes/(?P<mobile>1[3-9]\d{9})/', views.WeiboSMSCodeView.as_view()),
]