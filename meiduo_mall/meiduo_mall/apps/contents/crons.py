from collections import OrderedDict
from django.conf import settings
from django.template import loader
import os
import time

from goods.models import GoodsChannel
from .models import ContentCategory


def generate_static_index_html():
    """
    生成静态的主页html文件
    """

    # 商品频道及分类菜单
    # 使用有序字典保存类别的顺序
    # categories = {
    #     1: { # 组1
    #         'channels': [ {'id':, 'name':, 'url':},{}, {}...],
    #         'sub_cats': [ {'id':, 'name':, 'sub_cats':[{},{}]},
    #                       {'id':, 'name':, 'sub_cats':[{},{}]},
    #                       {}, ..]
    #     },
    #     2: { # 组2
    #
    #     }
    # }
    try:

        categories = OrderedDict()

        channels = GoodsChannel.objects.order_by('group_id', 'sequence')
        for channel in channels:
            group_id = channel.group_id
            if group_id not in categories:
                categories[group_id] = {'channels': [], 'sub_cats': []}

            cat1 = channel.category
            categories[group_id]['channels'].append({
                'id': cat1.id,
                'name': cat1.name,
                'url': channel.url
            })
            # goodscategory_set
            for cat2 in cat1.goodscategory_set.all():
                cat2.sub_cats = []
                for cat3 in cat2.goodscategory_set.all():
                    cat2.sub_cats.append(cat3)
                categories[group_id]['sub_cats'].append(cat2)

        contents = {}
        content_categories = ContentCategory.objects.all()
        for cat in content_categories:
            contents[cat.key] = cat.content_set.filter(status=True).order_by('sequence')

        context = {
            'categories': categories,
            'contents': contents
        }
        template = loader.get_template('index.html')
        html_text = template.render(context)
        file_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR, 'index.html')
        with open(file_path, 'w', encoding='utf-8')as f:
            f.write(html_text)
    except Exception as e:
        print("%s:generate static index html error happened :%s" %(time.ctime(), e))
    else:
        print("%s:generate static index html succeed" %(time.ctime()))
