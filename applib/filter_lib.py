import os
import sys
import jieba
if __name__ == '__main__':
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
#-#from applib.tools_lib import pcformat
from applib.conf_lib import getConf
from applib.log_lib import app_log
info, debug, warn, error = app_log.info, app_log.debug, app_log.warning, app_log.error


class FilterTitle(object):
    def __init__(self, conf_path, event_notify):
        self.conf_path = os.path.abspath(conf_path)
        self.conf = getConf(self.conf_path, root_key='filter')

        self.event_notify = event_notify
        self.filter_path = os.path.abspath(self.conf['filter_path'])

        self.st_include = set()
        self.st_exclude = set()
        self._loadIncludeExcludeData()

        jieba.dt.tmp_dir = self.conf.get('jieba_tmp_dir', '')
        self.jieba_userdict_path = os.path.abspath(self.conf['jieba_userdict_path'])
        if self.jieba_userdict_path and os.path.exists(self.jieba_userdict_path):
            self.jieba_userdict = jieba.load_userdict(self.jieba_userdict_path)
        else:
            self.jieba_userdict = None
        self.jieba_strip_word = self.conf['jieba_strip_word']

    def _loadIncludeExcludeData(self, force_reload=False):
        conf = getConf(self.filter_path, force_reload=force_reload)
        self.st_include, self.st_exclude = set(conf['l_include']), set(conf['l_exclude'])
        info('%s/%s include/exlude item(s) loaded', len(self.st_include), len(self.st_exclude))

    def cutWord_jieba(self, s):
        l_word = list(filter(None, map(lambda x: x.strip(self.jieba_strip_word), jieba.cut(s, cut_all=False))))
        warn('%s <= %s', '/'.join(l_word), s)
        return l_word

    def matchFilter(self, **kwargs):
        """
        'SKIP', '<SKIP_WORD>'
        'NOTIFY', '<NOTIFY_WORD>'
        'NORMAL', ''
        """
        action, word = '', ''
        title = kwargs.get('title', '')
        # reload modified filter data
        if self.event_notify.is_set():
            self._loadIncludeExcludeData(force_reload=True)
            self.event_notify.clear()

        st_word = set(self.cutWord_jieba(title))
        if self.st_exclude & st_word:
            action, word = 'SKIP', '/'.join(self.st_exclude & st_word)
        elif self.st_include & st_word:
            action, word = 'NOTIFY', '/'.join(self.st_include & st_word)
        else:
            action = 'NORMAL'

        return action, word

