from celery_tasks.main import celery_app
from django.template import loader
import os
from django.conf import settings

from goods.utils import get_categories
from goods.models import SKU

@celery_app.task(name='generate_static_list_search_html')
def generate_static_list_search_html():
    """
    生成静态的商品列表页和搜索结果页html文件
    :return:
    """
    categories = get_categories()
    context = {
        'categories':categories
    }
    template = loader.get_template('list.html')
    html_text = template.render(context)
    file_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR,'list.html')
    with open(file_path,'w') as f:
        f.write(html_text)

@celery_app.task(name='generate_static_sku_detail_html')
def generate_static_sku_detail_html(sku_id):
    """
    生成静态商品详情页面
    :param sku_id: 商品sku id
    """
    categories = get_categories()

    sku = SKU.objects.get(id = sku_id)
    sku.images = sku.skuimage_set.all()

    goods = sku.goods
    goods.channel = goods.category1.goodschannel_set.all()[0]

    sku_specs = sku.skuspecification_set.order_by('spec_id')
    sku_key = []
    for spec in sku_specs:
        sku_key.append(spec.option.id)

    skus = goods.sku_set.all()

    spec_sku_map = {}
    for s in skus:
        s_specs = s.skuspecification_set.order_by('spec_id')
        key = []

        for spec in s_specs:
            key.append((spec.option.id))

        spec_sku_map[tuple(key)] = s.id

        specs = goods.goodsspecification_set.order_by('id')

        if len(sku_key) < len(specs):
            return
        for index ,spec in enumerate(specs):
            key = sku_key[:]
            options = spec.specificationoption_set.all()

            for option in options:
                key[index] = option.id
                option.sku_id = spec_sku_map.get(tuple(key))

            spec.options = options

        context = {
            'categories':categories,
            'goods':goods,
            'specs':specs,
            'sku':sku
        }
        template = loader.get_template('detail.html')
        html_text = template.render(context)
        file_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR,
                                 'goods/'+str(sku_id)+'.html')
        with open(file_path, 'w') as f:
            f.write(html_text)