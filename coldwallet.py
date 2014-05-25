#!/usr/bin/env python

import sys

# pybitcointools from (e.g.) github.com:vbuterin/pybitcointools.git
try:
    from pybitcointools.main import *
except ImportError:
    from bitcoin.main import *

from PIL import Image, ImageFont, ImageOps, ImageChops, ImageDraw
import qrcode
from bip38 import *

def add_border(im, border_width, color):
    size = im.size
    new_size = (size[0] + border_width * 2, size[1] + border_width * 2)
    new_im = Image.new(im.mode, new_size, color)
    new_im.paste(im, (border_width, border_width))
    return new_im

def trim(im):
    bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)

def make_qr(text, size, border_size, invert=False):
    qr = qrcode.make(text)
    w, h = qr.size
    qr = trim(qr)
    content_size = size - border_size * 2
    qr = qr.resize((content_size, content_size))
    qr = qr.convert("RGB")
    if invert:
        qr = ImageOps.invert(qr)
        qr = add_border(qr, border_size, "black")
    return qr

def card_wallet(password, invert_qr=False, border=0):
    key = random_key()
    address = privkey_to_address(key)
    key_enc = bip38_encrypt(encode_privkey(key, 'wif'), password)
    print "%s  --  %s" % (address, key_enc)
    w, h = (2100, 1200)
    top_margin = 170
    side_margin = 60
    qr_border = 0
    if invert_qr:
        qr_border = side_margin
    qr_size = h - 2 * top_margin

    canvas = Image.new("RGB", (w, h), "white")
    key_qr = make_qr(key_enc, qr_size, qr_border, invert_qr)
    address_qr = make_qr(address, qr_size, qr_border, invert_qr)
    canvas.paste(address_qr, (side_margin, top_margin))
    canvas.paste(key_qr, (w - side_margin - qr_size, top_margin))
    big_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.dfont", 84, 4)
    small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.dfont", 50, 4)
    draw = ImageDraw.Draw(canvas)
    text_sep = 30

    addr_w, addr_h = draw.textsize(address, font=big_font)
    key_w, key_h = draw.textsize(key_enc, font=small_font)
    draw.text((side_margin, top_margin - addr_h - text_sep), address, font=big_font, fill="black")
    draw.text((w - side_margin - key_w, top_margin + qr_size + text_sep + 10), key_enc, font=small_font, fill="black")

    btc_size = 240
    btc = Image.open("btcblur.png").resize((100, 100)).convert("RGB")
    btc = btc.resize((btc_size, btc_size), Image.ANTIALIAS)
    canvas.paste(btc, (w/2 - btc_size/2, h/2 - btc_size/2))

    if border:
        lines = [ [0,0,w,0], [0,0,0,h], [w,0,w,h], [0,h,w,h]]
        for line in lines:
            draw.line(line, "black", border)
    return canvas

def paper_wallet(password):
    dpi = 600
    paper = Image.new("RGB", (int(8.5 * dpi), int(11 * dpi)), "white")
    h_sep = int((8.5 - 2 * 3.5) / 3.0 * dpi)
    v_sep = int((11 - 4 * 2) / 5.0 * dpi)
    for i in range(0,2):
        for j in range(0, 4):
            wallet = card_wallet(password, border=16)
            ww, wh = wallet.size
            x = h_sep + i * (ww + h_sep)
            y = v_sep + j * (wh + v_sep)
            paper.paste(wallet, (x,y))
    paper = paper.resize((paper.size[0] / 2, paper.size[1] / 2))
    return paper

if __name__ == '__main__':
    try:
        cmd = sys.argv[1]
        password = sys.argv[2]
        filename = "wallet.png"
        if len(sys.argv) > 3:
            filename = sys.argv[3]
        wallet = None
        if cmd == 'card':
            wallet = card_wallet(password)
        elif cmd == 'laser':
            wallet = card_wallet(password, invert_qr=True)
        elif cmd == 'paper':
            wallet = paper_wallet(password)
        else:
            raise Error("unknown command")
        wallet.save(filename)
    except:
        print """
Usage:
    coldwallet.py card <password> <filename.png>
      Generates a business-card sized image with 1 BIP38 cold wallet

    coldwallet.py laser <password> <filename.png>
      Generates a business-card sized image designed for laser engraving on anodized aluminum

    coldwallet.py paper <password> <filename.png>
      Generates an 8.5x11 @ 300dpi image with 8 BIP38 cold wallets

    If filename is not provided, output will be to wallet.png by default

"""
