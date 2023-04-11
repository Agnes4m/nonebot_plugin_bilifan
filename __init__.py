import json
import os
import sys
from nonebot.log import logger
import warnings
import asyncio
import aiohttp
import itertools
from pathlib import Path
from .main import *
from .src import BiliUser


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

local_path = Path(__file__).parent


print(local_path)


fan_once = on_command('bfan',aliases={'开始刷牌子'},block=True)

@fan_once.handle()
async def _():
    await strat_once()
    fan_once.finish('成功')
