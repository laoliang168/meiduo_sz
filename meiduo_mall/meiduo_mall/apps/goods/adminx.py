import xadmin
from xadmin import views

from . import models
from celery_tasks.html.tasks import generate_static_list_search_html, generate_static_sku_detail_html


class GoodsCategoryAdmin(object):
    # 模型站点管理类,不光可以控制admin的页面展示样式,还可以监听它里面的数据变化

    def save_models(self):
        """
        监听运营人员在admin界面点击了商品分类数据保存事件
        :param request: 本次保存时的请求对象
        :param obj: 本次要保存的模型对象
        :param form: 要进行修改的表单数据
        :param change: 是否要进行修改 True或False
        :return:
        """
        obj = self.new_obj
        obj.save()
        generate_static_list_search_html.delay()

    def delete_model(self):
        """
        监听运营人员在admin界面点击了商品分类数据删除
        :param request: 本次删除时的请求对象
        :param obj: 要删除的模型对象
        :return:
        """
        obj = self.obj
        obj.delete()
        generate_static_list_search_html.delay()


class SKUAdmin(object):
    """sku商品"""
    model_icon = 'fa fa-gift'  # 设置小图标

    list_display = ['id', 'name', 'price', 'comments']
    list_filter = ['category', 'name', 'id']

    def save_models(self):
        obj = self.new_obj
        obj.save()
        generate_static_sku_detail_html.delay(obj.id)
        # generate_static_sku_detail_html(obj.id)


class SKUImageAdmin(object):
    """SKU中的图片"""

    def save_models(self):
        obj = self.new_obj
        obj.save()

        sku = obj.sku  # 获取图片所对应的sku
        if sku.default_image_url == None:  # 如果当前sku没有默认的图片
            sku.default_image_url = obj.image.url  # 把当前的图片路径设置到sku中

        generate_static_sku_detail_html.delay(sku.id)

    def delete_model(self):
        obj = self.obj
        obj.delete()
        generate_static_sku_detail_html.delay(obj.sku.id)


xadmin.site.register(models.GoodsCategory, GoodsCategoryAdmin)
xadmin.site.register(models.GoodsChannel)
xadmin.site.register(models.Goods)
xadmin.site.register(models.Brand)
xadmin.site.register(models.GoodsSpecification)
xadmin.site.register(models.SpecificationOption)
xadmin.site.register(models.SKU, SKUAdmin)
xadmin.site.register(models.SKUSpecification)
xadmin.site.register(models.SKUImage, SKUImageAdmin)


class GlobalSettings(object):
    """xadmin的全局配置"""
    site_title = "美多商城运营管理系统"  # 设置站点标题
    site_footer = "美多商城集团有限公司"  # 设置站点的页脚
    menu_style = "accordion"  # 设置菜单折叠


xadmin.site.register(views.CommAdminView, GlobalSettings)


class BaseSetting(object):
    """xadmin的基本配置"""
    enable_themes = True  # 开启主题切换功能
    use_bootswatch = True  # 使用更多主题


xadmin.site.register(views.BaseAdminView, BaseSetting)
