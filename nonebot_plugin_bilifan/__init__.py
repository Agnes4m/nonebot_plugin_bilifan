from pathlib import Path
import shutil
from .main import *
from .src import BiliUser

from .login import get_tv_qrcode_url_and_auth_code,draw_QR,verify_login

from nonebot.log import logger
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageSegment,MessageEvent
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



login_in = on_command('blogin',aliases={'b站登录'},block=False)

@login_in.handle()
async def _(event:MessageEvent):
    try:
        login_url, auth_code = await get_tv_qrcode_url_and_auth_code()
    except aiohttp.client_exceptions.ClientTimeoutError:
        await login_in.finish("已超时，请稍后重试！")
    data_path = Path().joinpath(f'data/bilifan/{event.user_id}')
    data_path.mkdir(parents=True, exist_ok=True)
    data = await draw_QR(login_url)
    try:
        await login_in.send(MessageSegment.image(data))
    except:
        logger.warning('二维码可能被风控，发送链接')
        await login_in.send("或将此链接复制到手机B站打开:"+login_url)
    while True:
        a = await verify_login(auth_code,data_path)
        if a:
            await login_in.send(f"登录成功！\nqq:{event.user_id}\n{a}")
            break
        else:
            await login_in.finish("登录失败！")

fan_once = on_command('bfan',aliases={'开始刷牌子'},block=False)

@fan_once.handle()
async def _(event:MessageEvent):
    data_path = Path().joinpath(f'data/bilifan/{event.user_id}')
    data_path.mkdir(parents=True, exist_ok=True)
    msg_path = Path().joinpath(f'data/bilifan/{event.user_id}/login_info.txt')
    if msg_path.is_file:
        logger.info(msg_path)
        await fan_once.send('开始执行~')
    else:
        logger.info(msg_path)
        await fan_once.finish('你尚未登录，请输入【b站登录】')
    messageList = await main(msg_path.parent)
    await fan_once.finish(msg for msg in messageList)
    
if not os.path.exists(Path().joinpath('data/bilifan/users.yaml')):
    logger.info('初始化配置文件')
    shutil.copy2(Path(__file__).parent.joinpath('users.yaml'), Path().joinpath('data/bilifan/users.yaml'))