import sys
import os
import pickle
from urllib.parse import quote, urlparse
import asyncio
if __name__ == '__main__':
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from applib.tools_lib import pcformat
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from applib.conf_lib import getConf
from applib.net_lib import NetManager
from applib.log_lib import app_log
info, debug, warn, error = app_log.info, app_log.debug, app_log.warning, app_log.error

from logging import WARNING

class TODSManager(object):
    """获取SKU 信息
    """
    
    def __init__(self, conf_path='config/pn_conf.yaml', event_notify=None):
        self.conf_path = os.path.abspath(conf_path)
        self.conf = getConf(self.conf_path, root_key='tods')
        
        self.loop = None
        self.event_notify = event_notify
        self.net = NetManager(conf_path=self.conf_path, loop=self.loop, event_notify=self.event_notify)
        
    async def reverse(self, url):
        url_parsed = urlparse(url)
        try:
            if 'jd.com' in url_parsed.netloc:
                info('jd');
            elif 'taobao.com' in url_parsed.netloc:
                if 'uland.taobao.com' == url_parsed.netloc:
                    url = '{}/fansurltoid?apkey={}&fansurl={}'.format(self.conf['gateway'], self.conf['apkey'], quote(url))
                elif 's.click.taobao.com' == url_parsed.netloc:
                    url = '{}/sclicktoid?apkey={}&sclickurl={}'.format(self.conf['gateway'], self.conf['apkey'], quote(url))

                resp, text, ok = await self.net.getData(url, timeout=5, my_fmt='json')
                if ok:
                    info(('taobao', text['data']))
                    info(text)
                    if text['code'] == 200:
                        return 'taobao', text['data']

            return False

        except Exception as e:
            debug(e)
            
if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    try:
        tods = TODSManager()
        #task = asyncio.ensure_future(tods.reverse('https://uland.taobao.com/coupon/edetail?e=EQ1toYW4wrUGQASttHIRqYu8A2KAHzaN0RtTq3YXl73DnIjAZosmr1Vnak/nb7p8bmBWMncy98RgeXsNhrdqTgEWVZsPFdM8PD2GvGPQUfkbsbrLw191v%2Bdth9k8bqqSHKTgBzHkoM7XTQC0vfau6E/9Zk7cDx8UPY2GSU4OeGf02OGh5LJtvubEJl5ZJ47c&traceId=0b08441815593046455135415e&union_lens=lensId:0bb698e5_0c2f_16b0dccaba1_8b53&xId=U2vETTg7NdciS8sWjnIj463H6cVIdFL94hMCv2wjHbTTCv13OvMds4wL8MezIuDWRQIiUzyTL95a8hCNpe1CAt'))
        task = asyncio.ensure_future(tods.reverse('https://s.click.taobao.com/t?e=m%3D2%26s%3DeZjwDyoTrsAcQipKwQzePOeEDrYVVa64yK8Cckff7TVRAdhuF14FMY5muNi530JKxq3IhSJN6GSbBjBh3LodcDtMDMUFdHxsSOgE%2F%2FcSI3SyJaf7y6OSVItgwMO1YqTJ4q%2BRXokHRqt22bWK6RCIqBihUpzFc4OPhpf6hVB%2F01qN%2FkHiTKSuCuCTnndEcWujNmWRMvij917n15d31sYa31nXNw4RoQJURfoP8u5NmIXGJe8N%2FwNpGw%3D%3D&union_lens=lensId:0bb39b78_1875_16b0dc97153_1d8c'))
        x = loop.run_until_complete(task)
        info(pcformat(x))
    except KeyboardInterrupt:
        info('cancel on KeyboardInterrupt..')
        task.cancel()
        loop.run_forever()
        task.exception()


