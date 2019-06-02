import sys
import os
import re
import asyncio
from urllib.parse import quote, urlparse
if __name__ == '__main__':
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from applib.tools_lib import pcformat
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from applib.tods_lib import TODSManager
from applib.log_lib import app_log
info, debug, warn, error = app_log.info, app_log.debug, app_log.warning, app_log.error

class SkuExtractor(object):

    def __init__(self, url):
        self.url = url
        self.url_parsed = urlparse(self.url)
    
    async def get(self):
        if 'taobao.com' in self.url_parsed.netloc or 'tmall.com' in self.url_parsed.netloc:
            return await self.getTaobao()
        if 'jd.com' in self.url_parsed.netloc:
            return self.getJD()

    def getJD(self):
        """https://item.jd.com/5544116.html     
           https://ccc-x.jd.com/dsp/cl?posid=1999&v=707&union_id=1000210271&pid=1672&tagid=106153&didmd5=__IMEI__&idfamd5=__IDFA__&did=__IMEIIMEI__&idfa=__IDFAIDFA__&to=https%3A%2F%2Fitem.jd.com%2F11209741.html
        """
        skuid = re.search(r'(%2F)?(\d{7,})\.html', self.url)
        if skuid is not None:
            skuid = skuid.group(2)
            return 'jd', skuid
            
        return False

    async def getTaobao(self):
        """https://detail.taobao.com/item.htm?id=568824580534
           https://detail.tmall.com/item.htm?id=565677458062&skuId=3750009938897&pid=mm_25282911_3455987_64914100069
           https://s.click.taobao.com/t?e=m%3D2%26s%3DKRGrPMDi0cAcQipKwQzePOeEDrYVVa64yK8Cckff7TVRAdhuF14FMVIuivFVDqQ%2Blovu%2FCElQOubBjBh3LodcDtMDMUFdHxspIor9u9EYVUgGMcZH%2FjvZ4tgwMO1YqTJ4q%2BRXokHRqt22bWK6RCIqBihUpzFc4OPJ%2BYL8D8%2FnTe1%2BAIBtIGZWuCTnndEcWujCs4Dokz7zBwToygREbJK0lnXNw4RoQJURfoP8u5NmIXGJe8N%2FwNpGw%3D%3D&union_lens=lensId:0bb39b78_1875_16b0dccda61_375e
           https://uland.taobao.com/coupon/edetail?e=W74Y5jWQffIGQASttHIRqbkuTnJh4OFwRfTlVR1J6jXDnIjAZosmr1Vnak/nb7p8bmBWMncy98RgeXsNhrdqTgEWVZsPFdM8PD2GvGPQUfkbsbrLw191v0gfTscre/nAHKTgBzHkoM7rgK1krKqXyxvnZrWr9AQgw6G2NNlamjr02OGh5LJtvigiFSHaqHtP&traceId=0b0163aa15593042798402306e&union_lens=lensId:0b156441_0b5f_16b0dc71752_5f07&xId=b4TGKBuq4QEUKYlsXdYikqpONjws08oW6pJL1PaMGUzYXMKNvP9RWIeCcUMYDDHBjoXgWSkOLvDx4SOjMjImnv
        """
        if self.url_parsed.netloc in ['s.click.taobao.com', 'uland.taobao.com']:
            tods = TODSManager()
            result = await tods.reverse(self.url)
            info((result))
        else:
            item = re.search(r'item\.htm\?id=(\d+)', self.url)
            if item is not None:
                item = item.group(1)
                return 'taobao', item
                
        return False
    
    def getSuning(self):
        """https://product.suning.com/0000000000/168740738.html?utm_source=union&utm_medium=14&adtype=5&utm_campaign=38a8efab-b6e6-4218-b147-afb410875e93&union_place=un
        """
        skuid = re.search(r'(\d+)\.html$', self.url)
        if skuid is not None:
            skuid = skuid.group(1)
            return 'suning', skuid

        return False

    def getKaola(self):
        """https://www.kaola.com/product/1811503.html
        """

        skuid = re.search(r'/product/(\d+)\.html', self.url)
        if skuid is not None:
            skuid = skuid.group(1)
            return 'kaola', skuid

        return False

    def getDangdang(self):
        """http://product.dangdang.com/1141440504.html
        """
        skuid = re.search(r'(\d+)\.html$', self.url)
        if skuid is not None:
            skuid = skuid.group(1)
            return 'dangdang', skuid

        return False

    def getAmazon(self):
        """https://www.amazon.cn/dp/b01i570pyu
        """

        skuid = re.search(r'dp/([\d\w]+)$', self.url)
        if skuid is not None:
            skuid = skuid.group(1)
            return 'amazon', skuid

        return False

    def getSundan(self):
        """https://www.sundan.com/product-21868.html
        """

        skuid = re.search(r'product-(\d+)\.html$', self.url)
        if skuid is not None:
            skuid = skuid.group(1)
            return 'sundan', skuid

        return False

    def getWangyi(self):
        """https://you.163.com/item/detail?id=1648016
        """
        
        skuid = re.search(r'detail\?id=(\d+)', self.url)
        if skuid is not None:
            skuid = skuid.group(1)
            return 'wangyi', skuid

        return False

    def getXiji(self):
        """https://www.xiji.com/product-93600.html
        """
        
        skuid = re.search(r'/product-(\d+)\.html', self.url)
        if skuid is not None:
            skuid = skuid.group(1)
            return 'xiji', skuid

        return False
        
    def getGap(self):
        """https://www.gap.cn/product/2019658.html
        """
        skuid = re.search(r'(\d+)\.html$', self.url)
        if skuid is not None:
            skuid = skuid.group(1)
            return 'gap', skuid

        return False

    def getShoprobam(self):
        """https://www.shoprobam.com/Products/detail/gid/1470?utm_source=zhidemai
        """

        skuid = re.search(r'/gid/(\d+)\??', self.url)
        if skuid is not None:
            skuid = skuid.group(1)
            return 'shoprobam', skuid

        return False

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    try:
        #se = SkuExtractor('https://s.click.taobao.com/t?e=m%3D2%26s%3DeZjwDyoTrsAcQipKwQzePOeEDrYVVa64yK8Cckff7TVRAdhuF14FMY5muNi530JKxq3IhSJN6GSbBjBh3LodcDtMDMUFdHxsSOgE%2F%2FcSI3SyJaf7y6OSVItgwMO1YqTJ4q%2BRXokHRqt22bWK6RCIqBihUpzFc4OPhpf6hVB%2F01qN%2FkHiTKSuCuCTnndEcWujNmWRMvij917n15d31sYa31nXNw4RoQJURfoP8u5NmIXGJe8N%2FwNpGw%3D%3D&union_lens=lensId:0bb39b78_1875_16b0dc97153_1d8c');
        se = SkuExtractor('https://ccc-x.jd.com/dsp/cl?posid=1999&v=707&union_id=1000023384&pid=1643&tagid=102804&didmd5=__IMEI__&idfamd5=__IDFA__&did=__IMEIIMEI__&idfa=__IDFAIDFA__&to=https%3A%2F%2Fitem.jd.com%2F32207144052.html');
        task = asyncio.ensure_future(se.get())
        x = loop.run_until_complete(task)
        info(pcformat(x))
    except Exception as e:
        info(e)

