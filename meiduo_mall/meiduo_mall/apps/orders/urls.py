from django.conf.urls import url

from . import views

urlpatterns = [
    # 去结算
    url(r'^orders/settlement/$', views.OrderSettlementView.as_view()),
    # 保存订单
    url(r'^orders/$', views.CommitOrderView.as_view()),
    # 评论商品
    url(r'^orders/(?P<order_id>\d+)/uncommentgoods/$', views.CommentsView.as_view()),
    url(r'^orders/(?P<order_id>\d+)/comments/$', views.CommentCommitView.as_view())
]