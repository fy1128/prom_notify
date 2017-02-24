import sys
import json
import pickle
from datetime import datetime
from datetime import timedelta
import time
import gzip
import os
from urllib.parse import urlparse
from urllib.parse import urljoin
from urllib.parse import parse_qs
from lxml import etree
import asyncio
import aiohttp
import configparser
import codecs
from aiohttp.errors import ClientTimeoutError
from aiohttp.errors import ClientConnectionError
#-#from aiohttp.errors import ClientDisconnectedError
from aiohttp.errors import ClientError
from aiohttp.errors import HttpBadRequest
from aiohttp.errors import ClientHttpProcessingError
from setproctitle import setproctitle
import subprocess
import concurrent
import signal
import re
import multiprocessing
import execjs
import webbrowser
from applib.conf_lib import getConf
from applib.audio_lib import PlaySound
from applib.qrcode_lib import QrCode
from applib.watch_lib import startWatchConf, stopWatchConf
from applib.filter_lib import FilterTitle
from applib.tools_lib import htmlentitydecode
from applib.tools_lib import pcformat
from applib.log_lib import app_log

info, debug, warn, error = app_log.info, app_log.debug, app_log.warning, app_log.error
event_notify = multiprocessing.Event()
event_exit = asyncio.Event()

premovetag = re.compile('(<.*?>)', re.M | re.S)
#-#exclude_first_div_tag = re.compile(r'\A<div.*?>(.*?)</div>\Z', re.M | re.S)
#-#exclude_first_td_tag = re.compile(r'\A<td.*?>\s*(.*?)\s*</td>\Z', re.M | re.S)
#-#exclude_first_comment_tag = re.compile(r'\A<!-- .*?-->(.*?)<!-- .*?-->\Z', re.M | re.S)
#-#exclude_first_a_tag = re.compile(r'\A<a.*?>\s*(.*?)\s*</a>\Z', re.M | re.S)


async def signal_handler(sig):
    if sig == signal.SIGINT:
        warn('got Ctrl+C')
        event_exit.set()


class PromNotify(object):
    """main class
    """
    def __init__(self, conf_file='./config/pn_conf.yaml', loop=None):
        # conf
        self.conf_file_path = os.path.abspath(conf_file)
        conf = getConf(self.conf_file_path)
        self.all_conf = conf
        self.conf = self.all_conf['prom_notify']
        # proc title
        setproctitle(self.all_conf['proc_title'])
        # session
        self.loop = loop
        self.sess = None
        if self.loop:
            self.sess = aiohttp.ClientSession(headers={'User-Agent': self.conf['user_agent']}, loop=self.loop)
        # history data
        self.history_file = os.path.abspath(self.conf['history_file'])
        self.history = {}
        # progress data
        self.progress_file = os.path.abspath(self.conf['progress_file'])
        self.progress = ProgressData(self.progress_file)
        # filter module
        self.filter = FilterTitle(self.conf_file_path, event_notify)
        # audio module
        self.ps = PlaySound(self.conf_file_path)
        # voice play processes
        self.voice = multiprocessing.Queue()

    async def init(self):
        if self.sess is None:
            self.sess = aiohttp.ClientSession(headers={'User-Agent': self.conf['user_agent']})

    def _loadDb(self):
        if os.path.exists(self.history_file):
            self.history = pickle.loads(gzip.open(self.history_file).read())
            debug('%d histroy data loaded.', len(self.history))

    def _saveDb(self):
        if len(self.history) > 0:
            info('saving data file (%d)...', len(self.history))
            gzip.open(self.history_file, 'wb').write(pickle.dumps(self.history))

    async def getPic(self, pic):
        '''获取图片数据
        '''
        picfilepath = '/tmp/fxx_tmp_icon.jpg'
        nr_try = 5
        while nr_try:
            pr = urlparse(pic)
            if not pr.scheme:
                new_pic = urljoin('http://', pic)
                warn('pic %s -> %s', pic, new_pic)
                pic = new_pic
            try:
                pr = await self.sess.get(pic, timeout=5)
            except ClientTimeoutError:
                error('ReadTimeout pic get error %s', pic)
                await asyncio.sleep(1)
                nr_try -= 1
            except ClientConnectionError:
                error('ConnectionError pic get error %s', pic)
                await asyncio.sleep(1)
                nr_try -= 1
            except ClientError:
                error('pic get error %s', pic)
                break
            except HttpBadRequest:
                error('InvalidSchema pic get error %s', pic)
                break
            else:
                if pr.status == 200:
                    open(picfilepath, 'wb').write(pr.content)
                else:
                    warn('pic get status_code %s for %s', pr.status, pic)
                break
            finally:
                if pr:
                    await pr.release()

        return picfilepath

    async def _notify(self, **kwargs):
        action, ret_data = 'SKIP', 'IGNORE'
        slience, title, real_url, pic, sbr_time, item_url, from_title = \
            list(map(lambda x, k=kwargs: k.get(x, ''), ('slience', 'title', 'real_url', 'pic', 'sbr_time', 'item_url', 'from_title')))

        if not slience:
            action, word = self.filter.matchFilter(**kwargs)
            if action == 'NOTIFY':
                action, ret_data = '', word
                # open browser
                cmd = 'notify-send  "%s" "%s at %s"' % (from_title, title.replace('$', '\$').replace('&', '＆'), sbr_time.strftime('%H:%M:%S'))
#-#                    debug('EXEC_CMD< %s ...\n%s %s', cmd, item_url, real_url)
                subprocess.Popen(cmd, shell=True).wait()
#-#                    # 禁掉open url
                info('ACCEPT open url for word %s in %s', word, title)
                pic_path = await self.getPic(pic)
                webbrowser.get('firefox').open_new_tab('file:///%s' % QrCode.getQrCode(real_url, pic=pic_path))
                self.ps.playText(title)
            elif action == 'NORMAL':
                action, ret_data = '', ''
                self.ps.playText(title)
            elif action == 'SKIP':
                ret_data = word

        return action, ret_data

#-#    async def _play_sound(self, content, tp='pyaudio'):
#-#        new_content = re.sub('(\d+-\d+)', lambda x: x.group(1).replace('-', '减'), content, re.U)
#-#    #-#    if new_content != content:
#-#    #-#        info('%s -> %s', content, new_content)
#-#        # call tts
#-#        rand = '%6d' % (random.random() * 1000000)
#-#        file_in = '/tmp/tmp_in_%s.txt' % rand
#-#        file_out = '/tmp/tmp_out_%s.pcm' % rand
#-#        open(file_in, 'wb').write(new_content.encode('utf8'))
#-#        self.t2s.short_t2s(file_in, file_out)
#-#        if not os.path.exists(file_out):
#-#            return
#-#
#-#        if tp == 'mplayer':
#-#    #-#        cmd = 'mplayer -demuxer rawaudio -rawaudio channels=1:rate=16000:bitrate=16 -softvol -volume 20 -ao alsa:device=hw=0.0 -novideo ./tmp_out.pcm'
#-#    #-#        cmd = 'mplayer -demuxer rawaudio -rawaudio channels=1:rate=16000:bitrate=16  -novideo ./tmp_out.pcm'
#-#            cmd = 'mplayer -demuxer rawaudio -rawaudio channels=1:rate=16000:bitrate=16 -softvol -volume 10 -novideo %s' % file_out
#-#            info('EXEC_CMD< %s ...', cmd)
#-#            subprocess.Popen(cmd, shell=True).wait()
#-#        elif tp == 'ao':
#-#            import ao
#-#            ao.AudioDevice('raw', bits=16, rate=16000, channels=1).play(open(file_out).read())
#-#        elif tp == 'pcm':
#-#            import alsaaudio
#-#    #-#        pcm = alsaaudio.PCM(card='hw:0,0')
#-#            pcm = alsaaudio.PCM(card='Intel')
#-#            pcm.setchannels(2)
#-#            pcm.setrate(16000)
#-#            pcm.setformat(alsaaudio.PCM_FORMAT_S16_LE)
#-#            # play pcm file from tts
#-#            pcm.write(open(file_out).read())
#-#            del pcm
#-#        elif tp == 'pyaudio':
#-#            subprocess.Popen('cmus-remote -u', shell=True).wait()
#-#            p = pyaudio.PyAudio()
#-#            stream = p.open(format=p.get_format_from_width(2), channels=1, rate=16000, output=True)
#-#            stream.write(open(file_out, 'rb').read())  # 播放获得到的音频
#-##-#                stream.stop_stream()
#-##-#                stream.close()
#-##-#                p.terminate()
#-#            subprocess.Popen('cmus-remote -u', shell=True).wait()
#-#
    async def getData(self, url, *args, **kwargs):
        """
        my_fmt:
            str:
                my_str_encoding
            json:
                my_json_encoding
                my_json_loads
            bytes:
                None
            streaming:
                my_streaming_chunk_size
                my_streaming_cb
        """
        resp, data, ok = None, None, False
        str_encoding = kwargs.pop('my_str_encoding', None)
        fmt = kwargs.pop('my_fmt', 'str')
        json_encoding = kwargs.pop('my_json_encoding', None)
        json_loads = kwargs.pop('my_json_loads', json.loads)
        streaming_chunk_size = kwargs.pop('my_streaming_chunk_size', 1024)
        streaming_cb = kwargs.pop('my_streaming_cb', None)
        max_try = kwargs.pop('my_retry', 1)

        for nr_try in range(max_try):
            try:
#-#                debug('url %s %s %s', url, pcformat(args), pcformat(kwargs))
                resp = await self.sess.get(url, *args, **kwargs)
                if fmt == 'str':
                    data = await resp.text(encoding=str_encoding)
                elif fmt == 'json':
                    data = await resp.json(encoding=json_encoding, loads=json_loads)
                elif fmt == 'bytes':
                    data = await resp.read()
                elif fmt == 'stream':
                    while 1:
                        chunk = await resp.content.read(streaming_chunk_size)
                        if not chunk:
                            break
                        streaming_cb(url, chunk)
                ok = True
                break
            except asyncio.TimeoutError:
                info('%sTimeoutError %s %s %s', ('%s/%s ' % (nr_try + 1, max_try)) if max_try > 1 else '', url, pcformat(args), pcformat(kwargs))
            except ClientConnectionError:
                error('%sConnectionError %s %s %s', ('%s/%s ' % (nr_try + 1, max_try)) if max_try > 1 else '', url, pcformat(args), pcformat(kwargs))
            except ClientHttpProcessingError:
                error('%sClientHttpProcessingError %s %s %s', ('%s/%s ' % (nr_try + 1, max_try)) if max_try > 1 else '', url, pcformat(args), pcformat(kwargs), exc_info=True)
            except ClientTimeoutError:
                error('%sClientTimeoutError %s %s %s', ('%s/%s ' % (nr_try + 1, max_try)) if max_try > 1 else '', url, pcformat(args), pcformat(kwargs))
            except ClientError:
                error('%sClientError %s %s %s', ('%s/%s ' % (nr_try + 1, max_try)) if max_try > 1 else '', url, pcformat(args), pcformat(kwargs), exc_info=True)
            finally:
                if resp:
                    resp.release()

        return resp, data, ok

    async def check_main_page_mmb(self):
        r, text, ok = await self.getData('http://cu.manmanbuy.com/cx_0_0_wytj_Default_1.aspx', timeout=10, my_str_encoding='gbk')
        if not ok:
            return

        if r.status != 200:
            info('got code %s for %s', r.status, r.url)
            return
        pr = etree.HTMLParser()
        tree = etree.fromstring(text, pr)
        l_item = tree.xpath('//ul[@id="lilist"]/li')
    #-#    info('got %s item(s)', len(l_item))

        try:
            for x in l_item:
                if event_exit.is_set():
                    info('got exit flag, exit~')
                    break
                _id = x.xpath('./div[@class="action"]/div[@class="popbox"]/dl/dd[1]/a/@data-id')[0][:]
                key = 'manmanbuy_%s' % _id
                if key in self.history:
                    continue
                title = x.xpath('./div[@class="tit"]/a/text()')[0][:].strip()
                price = x.xpath('./div[@class="price"]/text()')[0][:].strip()
                show_title = ' '.join((title, price))
    #-#            pic = x.xpath('./div[@class="pic"]/a/img/@src')[0][:]
                pic = x.xpath('./div[@class="pic"]/a/img/@original')[0][:]
                tim = x.xpath('./div[@class="other"]/span[@class="t"]/text()')[0][:]
                year = datetime.now().year
                tim = datetime.strptime('%s-%s' % (year, tim), '%Y-%m-%d %H:%M')
                url = x.xpath('./div[@class="golink"]/a/@href')[0][:]
                url = 'http://cu.manmanbuy.com/%s' % (url, )
                item_url = 'http://cu.manmanbuy.com/Sharedetailed_%s.aspx' % (_id, )
                # TODO get real url
                real_url = url
                if url is not None:
                    raw_url = url
                    nr_redirect = 0
                    while url.find('manmanbuy') != -1 and urlparse(url).path:
                        r, _, ok = await self.getData(url, timeout=5)
                        nr_redirect += 1
                        if ok:
                            if r.status == 200:
                                url = r.url
                                if 'url=' in url:  # found 'url=' or 'tourl='
                                    up = urlparse(url)
                                    d_p = parse_qs(up.query)
                                    for _k in ('url', 'tourl'):
                                        if _k in d_p:
                                            url = d_p[_k][0]
                                            break
                            else:
                                x = 'http://cu.manmanbuy.com/http'
                                if x in raw_url:
                                    url = raw_url[len(x) - 4:]
                                    if url[0] == 's':  # https
                                        url = url[1:]
#-#                                    debug('url from bad url: %s -> %s', raw_url, url)
                                else:
                                    info('real url not found %s %s %s', r.status, raw_url, r.url)
                                break
                            if nr_redirect > 5:
                                warn('too many redirect %s', real_url)
                                break

                    real_url = url

    #-#            print >> sys.stderr, ''  # return line
                pic = pic.replace('////', '//')
                action, data = await self._notify(slience=self.conf['slience'], title=show_title, real_url=real_url, pic=pic, sbr_time=tim, item_url=item_url, from_title='慢慢买')
                (info if action != 'SKIP' else debug)('%sadding [%s] %s %s --> %s\n', (data + ' ') if data else '', tim, show_title, item_url, real_url)
                self.history[key] = (pic, show_title, item_url, real_url, tim)
        except:
            error('error ', exc_info=True)

    async def check_main_page(self):
        nr_new = 0
        max_time, min_time = time.time(), time.time()

        base_url = '''http://www.smzdm.com/youhui/'''
    #-#    debug('base_url = %s', base_url)
        real_url = None
        r, text, ok = await self.getData(base_url, timeout=5)
        if ok:
            if ok and r.status == 200:
                pr = etree.HTMLParser()
                tree = etree.fromstring(text, pr)
                l_item = tree.xpath('/html/body/section[@class="wrap"]//div[@class="list list_preferential "]')
                for x in l_item:
                    if event_exit.is_set():
                        info('got exit flag, exit~')
                        break
                    url = x.xpath('./div[@class="listTitle"]//h2[@class="itemName"]/a/@href')[0][:]
                    direct_url = None
                    try:
                        direct_url = x.xpath('./div[@class="listRight"]/div[@class="lrBot"]/div[@class="botPart"]/div[@class="buy"]/a/@href')[0]
                    except IndexError:
                        pass
                    title = premovetag.sub('', htmlentitydecode(etree.tostring(x.xpath('./div[@class="listTitle"]//h2[@class="itemName"]/a')[0]).decode('utf8')))
                    title_price = x.xpath('./div[@class="listTitle"]//h2[@class="itemName"]/a/span[@class="red"]/text()')
                    if title_price:
                        title_noprice = premovetag.sub('', x.xpath('./div[@class="listTitle"]//h2[@class="itemName"]/a/text()')[0][:])
    #-#                    info('title_noprice: %s', title_noprice)
                        show_title = title_noprice + ' ' + title_price[0][:]
                    else:
                        show_title = title

                    pic = x.xpath('./a[@class="picLeft"]/img/@src')[0][:]
                    _id = x.attrib['articleid']
                    item_id = 'p' + _id[_id.find('_') + 1:]
                    timesort = int(x.attrib['timesort'])
                    sbr_time = datetime.fromtimestamp(timesort)
                    if min_time is None or timesort < min_time:
                        min_time = timesort
                    if max_time is None or timesort > max_time:
                        max_time = timesort
                    if item_id not in self.history:
                        nr_new += 1
                        # get real url
                        real_url = None
                        if direct_url is not None:
                            if direct_url.find('/go.smzdm.com/') != -1:
    #-#                            debug('getting real_url for %s ...', direct_url)
                                rr, rr_text, ok = await self.getData(direct_url, timeout=5)
                                if ok and rr.status == 200:
                                    s_js = re.search(r'eval\((.+?)\)\s+\</script\>', rr_text, re.DOTALL | re.IGNORECASE | re.MULTILINE | re.UNICODE).group(1)
                                    s_rs = execjs.eval(s_js)
#-#                                    debug('s_rs: %s', repr(s_rs))
                                    s_key = re.search(r'location\.href=(.+?)}', s_rs).group(1)
#-#                                    debug('s_key: %s', repr(s_key))
                                    m = re.search(r'''%s='(?P<real_url>.+?)';''' % (s_key,), s_rs, re.DOTALL | re.IGNORECASE | re.MULTILINE | re.UNICODE)
                                    if m:
                                        real_url = m.group('real_url')
#-#                                        debug('real_url: %s', real_url)
                                    else:
                                        info('can\'t find real_url')
                            else:
                                real_url = direct_url[:]

                        if pic[0] == '/':
                            pic = 'http://www.smzdm.com%s' % pic

    #-#                    print >> sys.stderr, ''  # return line
                        err_msg, data = await self._notify(slience=self.conf['slience'], title=show_title, real_url=real_url, pic=pic, sbr_time=sbr_time, item_url=url, from_title='什么值得买')
                        (info if not err_msg else debug)('%sadding [%s] %s %s --> %s\n', (data + ' ') if data else '', sbr_time, show_title, url, real_url)
                        self.history[item_id] = (pic, show_title, url, real_url, sbr_time)
                    else:
                        pass
            else:
                info('return code = %d !!!', r.status)

        return nr_new, max_time, min_time

    async def check_main_page_getmore(self, process_time):
        nr_new = 0
        max_time, min_time = None, None
        base_url = '''http://www.smzdm.com/youhui/json_more'''
        debug('base_url = %s', base_url)
        real_url = None
        r, text, ok = await self.getData(base_url, params={'timesort': str(process_time)}, timeout=10, my_fmt='json')
        if ok:
            if r.status == 200:
                info('url %s', r.url)
                l_item = text
                for x in l_item:
                    if event_exit.is_set():
                        info('got exit flag, exit~')
                        break
                    url = x['article_url']
                    direct_url = x['article_link']
                    show_title = ' '.join((x['article_title'], x['article_price']))
                    sbr_time = datetime.fromtimestamp(x['timesort'])
                    pic = x['article_pic']
                    item_id = 'p' + x['article_id']
                    timesort = x['timesort']
                    if min_time is None or min_time > timesort:
                        min_time = timesort
                    if max_time is None or max_time < timesort:
                        max_time = timesort
                    if item_id not in self.history:
                        nr_new += 1
                        # get real url
                        real_url = None
                        if direct_url is not None:
                            real_url = None
                            if direct_url.find('/go.smzdm.com/') != -1:
                                debug('getting real_url for %s ...', direct_url)
                                rr, rr_text, ok = await self.getData(direct_url, timeout=5)
                                if ok and rr.status == 200:
                                    s_js = re.search(r'eval\((.+?)\)\s+\</script\>', rr_text, re.DOTALL | re.IGNORECASE | re.MULTILINE | re.UNICODE).group(1)
                                    s_rs = execjs.eval(s_js)
                                    s_key = re.search(r'location\.href=(.+?)}', s_rs).group(1)
                                    m = re.search(r'''%s='(?P<real_url>.+?)';''' % (s_key,), s_rs, re.DOTALL | re.IGNORECASE | re.MULTILINE | re.UNICODE)
                                    if m:
                                        real_url = m.group('real_url')
                                    else:
                                        warn('can\'t find real_url')

                        err_msg, data = await self._notify(slience=self.conf['slience'], title=show_title, real_url=real_url, pic=pic, sbr_time=sbr_time, item_url=url, from_title='什么值得买')
                        (info if not err_msg else debug)('%sadding [%s] %s %s --> %s\n', (data + ' ') if data else '', sbr_time, show_title, url, real_url)
                        if len(x['article_link_list']) > 0:
                            (info if not err_msg else debug)('have more url:\n%s', '\n'.join('%s %s %s' % (_url['name'], _url['buy_btn_domain'], _url['link']) for _url in x['article_link_list']))

                        self.history[item_id] = (pic, show_title, url, real_url, sbr_time)
            else:
                info('return code = %d !!!', r.status)

        return nr_new, max_time, min_time

    def clean(self):
        if self.sess:
            self.sess.close()

    async def do_work_smzdm(self):
        global event_exit
        process_time_sec = time.mktime(self.progress.process_time.timetuple())
        nr_new = None
        interval = self.conf['interval']
        while True:
            nr_new, max_process_time_sec, min_process_time_sec = await self.check_main_page()

            while min_process_time_sec >= process_time_sec:
                process_time_sec = min_process_time_sec
                nr_new, _, min_process_time_sec = await self.check_main_page_getmore(process_time_sec)

                if event_exit.is_set():
                    info('got exit flag, exit~')
                    break

                if min_process_time_sec is None:  # got net problem
                    min_process_time_sec = process_time_sec
                    await asyncio.sleep(5)
                    continue
                info('getmore nr_new %d min_sec %d(%s)', nr_new, min_process_time_sec, datetime.fromtimestamp(min_process_time_sec))

            process_time_sec = max_process_time_sec
            self.progress.process_time = datetime.fromtimestamp(process_time_sec)

            print('.', end='', file=sys.stderr, flush=True)
            if event_exit.is_set():
                info('got exit flag, exit~')
                break
#-#            await asyncio.sleep(interval)
            try:
                await asyncio.wait_for(event_exit.wait(), interval)
            except concurrent.futures._base.TimeoutError:
                pass
            if event_exit.is_set():
                info('got exit flag, exit~')
                break

    async def do_work_mmb(self):
        global event_exit
        interval = self.conf['interval']
        while True:
            await self.check_main_page_mmb()
            print('*', end='', file=sys.stderr, flush=True)
            if event_exit.is_set():
                info('got exit flag, exit~')
                break
#-#            await asyncio.sleep(interval)
            try:
                await asyncio.wait_for(event_exit.wait(), interval)
            except concurrent.futures._base.TimeoutError:
                pass
            if event_exit.is_set():
                info('got exit flag, exit~')
                break

    async def do_work_async(self):
        self.loop.add_signal_handler(signal.SIGINT, lambda: asyncio.ensure_future(signal_handler(signal.SIGINT)))
        await self.init()
        self._loadDb()
        wm, notifier, wdd = startWatchConf(self.all_conf['filter']['filter_path'], event_notify)

        info('doing ...')
        fut = [self.do_work_smzdm(), self.do_work_mmb()]
        try:
            await asyncio.gather(*fut)
        except concurrent.futures._base.CancelledError:
            info('Cancel after KeyboardInterrupt ? exit!')

        stopWatchConf(wm, notifier, wdd)
        self.clean()
        self.progress.saveCfg()

        self._saveDb()
        info('done.')


class ProgressData():
    '''维护处理进度信息
    '''
    def __init__(self, inifile='./config/fx_process.cfg', inifile_encoding='utf8'):
        super(ProgressData, self).__init__()

        self.__inifile_encoding = inifile_encoding
        self.__curdir = os.path.abspath(os.path.dirname(__file__))
        if os.path.abspath(os.curdir) != self.__curdir:
            os.chdir(self.__curdir)
        if not os.path.isabs(inifile):
            self.__inifile = os.path.join(self.__curdir, inifile)
        else:
            self.__inifile = inifile
        self.__cfg = None

        # cfg data
        self.process_time = None  # the time next  process begin with

        self.loadCfg()

    def loadCfg(self):
        self.__cfg = configparser.SafeConfigParser({'youhui_last_process_time': None, })
        if os.path.exists(self.__inifile):
            self.__cfg.readfp(codecs.open(self.__inifile, 'r', self.__inifile_encoding))
            debug('progress data loaded %s', self.__inifile)
        else:
            warn('progress data file not found ! %s', self.__inifile)

        self.process_time = self.__cfg.get('DEFAULT', 'youhui_last_process_time')
        if self.process_time in (None, 'None'):
            _tmp = (datetime.now() + timedelta(minutes=-10)).strftime('%Y%m%d_%H:%M:%S')
            self.process_time = datetime.strptime(_tmp, '%Y%m%d_%H:%M:%S')
        else:
            self.process_time = datetime.strptime(self.process_time, '%Y%m%d_%H:%M:%S')

    def saveCfg(self):
        self.__cfg.set('DEFAULT', 'youhui_last_process_time', self.process_time.strftime('%Y%m%d_%H:%M:%S'))
        with codecs.open(self.__inifile, 'w', self.__inifile_encoding) as _fo:
            self.__cfg.write(_fo)
        info('progress file saved. %s', self.__inifile)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    try:
        task = asyncio.ensure_future(PromNotify(loop=loop).do_work_async())
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        info('cancel on KeyboardInterrupt..')
        task.cancel()
        loop.run_forever()
        task.exception()
    finally:
        loop.stop()


