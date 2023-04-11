import json
import os
import sys
from nonebot.log import logger
import warnings
import asyncio
import aiohttp
import itertools
from .main import *
from .src import BiliUser
from .login import *


from nonebot import on_command, on_regex,get_driver
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.plugin import PluginMetadata


__version__ = "0.0.1"
__plugin_meta__ = PluginMetadata(
    name="bilifan",
    description='b站粉丝牌~',
    usage='自动刷b站粉丝牌',
    extra={
        "version": __version__,
        "author": "Agnes-Digital <Z735803792@163.com>",
    },
    )


login_in = on_command('blogin',aliases={'b站登录'},block=True)
@login_in.handle()
async def _():
    login_url, auth_code = await get_tv_qrcode_url_and_auth_code()
    await login_in.send(MessageSegment.image(await draw_QR(login_url)))
    await login_in.send("或将此链接复制到手机B站打开:", login_url)
    while True:
        if await verify_login(auth_code):
            print("登录成功！")
            break
        else:
            time.sleep(3)
            print("等待扫码登录中...")

fan_once = on_command('bfan',aliases={'开始刷牌子'},block=True)

@fan_once.handle()
async def _():
    await strat_once()
    fan_once.finish('成功')
