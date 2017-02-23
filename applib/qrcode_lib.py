import os
import sys
import qrcode
from PIL import Image
if __name__ == '__main__':
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from applib.log_lib import app_log
info, debug, warn, error = app_log.info, app_log.debug, app_log.warning, app_log.error


class QrCode(object):
    @staticmethod
    def getQrCode(url, **kwargs):
        '''生成二维码
        '''
        pic = kwargs.get('pic')
        f_name = '/tmp/fxx_tmp_qrcode.png'
        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H if pic else qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(url)
        qr.make(True)
        img = qr.make_image()
        img = img.convert('RGBA')
#-#        info('img %s %s', img.format, img.mode)
        if pic:
            icon = Image.open(pic)
            if img.format != 'PNG':
                convert_path = '/tmp/fxx_tmp_icon_convert_png.png'
                icon.save(convert_path)
                icon = Image.open(convert_path)
#-#                info('icon %s %s %s', icon.format, icon.mode, convert_path)
            img_w, img_h = img.size
            factor = 4
            size_w, size_h = int(img_w / factor), int(img_h / factor)
            icon_w, icon_h = icon.size
            if icon_w > size_w:
                icon_w = size_w
            if icon_h > size_h:
                icon_h = size_h
            icon = icon.resize((icon_w, icon_h), Image.ANTIALIAS)
            w = int((img_w - icon_w) / 2)
            h = int((img_h - icon_h) / 2)
#-#            img.paste(icon, (w, h), icon)
            img.paste(icon, (w, h))
        img.save(f_name)
        return f_name

