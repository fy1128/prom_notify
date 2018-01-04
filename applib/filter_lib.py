import os
import sys
import jieba
if __name__ == '__main__':
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from applib.tools_lib import pcformat
from applib.conf_lib import getConf
from applib.log_lib import app_log
info, debug, warn, error = app_log.info, app_log.debug, app_log.warning, app_log.error


class FilterTitle(object):
    def __init__(self, conf_path='config/pn_conf.yaml', event_notify=None):
        self.conf_path = os.path.abspath(conf_path)
        self.conf = getConf(self.conf_path, root_key='filter')

        self.event_notify = event_notify
        self.filter_path = os.path.abspath(self.conf['filter_path'])

        self.st_include = set()
        self.st_exclude = set()
        self.l_include_coupon = list()
        self.l_exclude_coupon = list()
        self._loadIncludeExcludeData()

        self.jieba_userdict_path = None
        self.jieba_userdict = None
        self.jieba_strip_word = None
        self._initJieba()

    def _loadIncludeExcludeData(self, force_reload=False):
        """重新从配置文件读取关注/排除词, 作为自定义词组添加到结巴
        """
        conf = getConf(self.filter_path, force_reload=force_reload)
        self.st_include, self.st_exclude = set(conf['l_include']), set(conf['l_exclude'])
        self.l_include_coupon = conf['l_include_coupon'] or []
        self.l_exclude_coupon = conf['l_exclude_coupon'] or []
        debug('include/exclude item(s) loaded. %s/%s ', len(self.st_include), len(self.st_exclude))
        debug('include/exclude coupon item(s) loaded. %s/%s ', len(self.l_include_coupon), len(self.l_exclude_coupon))
        if force_reload:
            self._addUserWord()

    def _addUserWord(self):
        """添加自定义词组
        """
        l_dynamic_word = sorted(self.st_include | self.st_exclude, key=lambda x: len(x) if x else 0, reverse=True)
        list(map(lambda w: jieba.add_word(w, freq=1500, tag=None) if w else 0, l_dynamic_word))
        debug('added %s include/exclude word(s) to jieba', len(l_dynamic_word))

    def _initJieba(self):
        """初始化结巴分词
        """
        jieba.dt.tmp_dir = self.conf.get('jieba_tmp_dir', '')
        self.jieba_userdict_path = os.path.abspath(self.conf['jieba_userdict_path'])
        if self.jieba_userdict_path and os.path.exists(self.jieba_userdict_path):
            self.jieba_userdict = jieba.load_userdict(self.jieba_userdict_path)
        else:
            self.jieba_userdict = None
        self._addUserWord()
        self.jieba_strip_word = self.conf['jieba_strip_word']

    def cutWordJieba(self, s):
        """分词
        """
        l_word = list(filter(None, map(lambda x: x.strip(self.jieba_strip_word), jieba.cut(s, cut_all=False))))
#-#        warn('%s <= %s', '/'.join(l_word), s)
        return l_word

    def matchFilter(self, **kwargs):
        """根据分词结果给出不同的动作建议(附带关注/排除词匹配结果和额外的分词细节)

        排除优先

        'SKIP', '<SKIP_WORD>', extra_data
        'NOTIFY', '<NOTIFY_WORD>', extra_data
        'NORMAL', '', extra_data
        """
        action, word, extra_data = '', '', {}
        title = kwargs.get('title', '')
        # reload modified filter data
        if self.event_notify is not None and self.event_notify.is_set():
            self._loadIncludeExcludeData(force_reload=True)
            self.event_notify.clear()

        l_word = self.cutWordJieba(title)
        extra_data['cut_word'] = l_word
        st_word = set(l_word)
        if self.st_exclude & st_word:
            action, word = 'SKIP', '/'.join(self.st_exclude & st_word)
        elif self.st_include & st_word:
            action, word = 'NOTIFY', '/'.join(self.st_include & st_word)
        else:
            action = 'NORMAL'

        return action, word, extra_data

    def matchFilterCoupon(self, **kwargs):
        """根据匹配结果给出不同的动作建议(附带关注/排除词匹配结果和额外的分词细节)

        排除优先

        'SKIP', '<SKIP_WORD>', extra_data
        'NOTIFY', '<NOTIFY_WORD>', extra_data
        'NORMAL', '', extra_data
        """
        action, word, extra_data = '', '', {}
        title = kwargs.get('title', '')
        # reload modified filter data
        if self.event_notify is not None and self.event_notify.is_set():
            self._loadIncludeExcludeData(force_reload=True)
            self.event_notify.clear()

        for _include_word in self.l_include_coupon:
            if _include_word in title:
                action, word = 'NOTIFY', _include_word
                break
        if not action:
            for _ignore_word in self.l_exclude_coupon:
                if _ignore_word in title:
                    action, word = 'SKIP', _ignore_word
                    break
            else:
                action = 'NORMAL'
        if not action:
            action = 'SKIP'

        return action, word, extra_data

    def clean(self):
        info('filter closed.')


if __name__ == '__main__':
#-#    from applib.tools_lib import pcformat
    t = FilterTitle()
#-#    x = t.cutWordJieba('傅雷译·约翰·克利斯朵夫')
#-#    x = t.cutWordJieba('连脚裤袜')
#-#    x = t.cutWordJieba('短毛绒汽车坐垫全包')
    x = t.cutWordJieba('世界经典文学名著 全译本')
    info(pcformat(x))

