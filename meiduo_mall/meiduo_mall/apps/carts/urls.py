from django.conf.urls import url

from . import views

urlpatterns=[
    url(r'^carts/$', views.CartView.as_view()),
    # 购物车全选
    url(r'^carts/selection/$', views.CartSelectedView.as_view()),
]