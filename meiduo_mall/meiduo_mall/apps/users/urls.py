from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from . import views
from rest_framework_jwt.views import obtain_jwt_token

urlpatterns = [
    url(r'^usernames/(?P<username>\w{5,20})/count/$', views.UsernameCountView.as_view()),
    url(r'^browse_histories/$',views.UserBrowseHistoryView.as_view()),
    url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
    url(r'^users/$', views.UserView.as_view()),
    url(r'^authorizations/$', views.UserAuthorizeView.as_view()),
    url(r'^user/$', views.UserDetailView.as_view()),
    url(r'^email/$', views.EmailView.as_view()),
    url(r'^emails/verification/$', views.EmailVerifyView.as_view()),
    url(r'^users/([1-9]+)/password/$', views.UpdataPasswordView.as_view()),
    url(r'^image_codes/[0-9a-zA-Z\-]+/$', views.ImageCode.as_view()),
    url(r'^sms_codes/$', views.FindPassSMSCodeView.as_view()),
    url(r'^accounts/(?P<username>.*)/sms/.*/$', views.VerifyNemasView.as_view()),  # 忘记密码-验证账户名和图片验证码
    url(r'^accounts/(?P<username>\w+)/password/token/$', views.VerifyMobileView.as_view()),  # 忘记密码-校验短信验证码
    url(r'^users/(?P<user_id>\d+)/password/forget/$', views.NewPassView.as_view())
]
router = DefaultRouter()
router.register(r'addresses', views.AddressViewSet, base_name='addresses')
urlpatterns += router.urls
