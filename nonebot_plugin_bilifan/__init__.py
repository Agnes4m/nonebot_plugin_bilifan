from pathlib import Path

from .utils import *
from .main import *
from .src import BiliUser
from .login import get_tv_qrcode_url_and_auth_code,draw_QR,verify_login

from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot import on_command
from nonebot import require,get_bot,get_driver
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import MessageSegment,MessageEvent,Message,GroupMessageEvent,PrivateMessageEvent
from nonebot.plugin import PluginMetadata
try:
    require("nonebot_plugin_apscheduler").scheduler
    from nonebot_plugin_apscheduler import scheduler
except BaseException:
    scheduler = None

logger.opt(colors=True).info(
    "已检测到软依赖<y>nonebot_plugin_apscheduler</y>, <g>开启定时任务功能</g>"
    if scheduler
    else "未检测到软依赖<y>nonebot_plugin_apscheduler</y>，<r>禁用定时任务功能</r>"
)

driver = get_driver()
__version__ = "0.1.4"
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
login_del = on_command('blogin_del',aliases={'删除登录信息'},block=False)
fan_once = on_command('bfan',aliases={'开始刷牌子','开始粉丝牌'},block=False)
fan_once = on_command('addfan',aliases={'自动刷牌子','自动粉丝牌'},priority=40,block=False)
del_only = on_command('bdel',aliases={'取消自动刷牌子','取消自动粉丝牌'},block=False)
del_all = on_command('bdel_all',aliases={'删除全部定时任务'},block=False,permission=SUPERUSER)

@login_in.handle()
async def _(matcher:Matcher,event:MessageEvent):
    try:
        login_url, auth_code = await get_tv_qrcode_url_and_auth_code()
    except aiohttp.client_exceptions.ClientTimeoutError:
        await matcher.finish("已超时，请稍后重试！")
    data_path = Path().joinpath(f'data/bilifan/{event.user_id}')
    data_path.mkdir(parents=True, exist_ok=True)
    data = await draw_QR(login_url)
    try:
        await matcher.send(MessageSegment.image(data))
    except:
        logger.warning('二维码可能被风控，发送链接')
        await matcher.send("或将此链接复制到手机B站打开:"+login_url)
    while True:
        a = await verify_login(auth_code,data_path)
        if a:
            await matcher.send(f"登录成功！\nqq:{event.user_id}\n{a}")
            break
        else:
            await matcher.finish("登录失败！")


@login_del.handle()
async def _(matcher:Matcher,event:MessageEvent):
    config = load_config()
    msg_path = Path().joinpath(f'data/bilifan/{event.user_id}/login_info.txt')   
    if msg_path.is_file(): 
        if event.user_id in config:
            del config[event.user_id]
            save_config(config)
            logger.info(f'已删除{event.user_id}的定时任务')
    try:
        data_path = Path().joinpath(f'data/bilifan/{event.user_id}')
        shutil.rmtree(data_path)
        await matcher.finish(f'已删除{event.user_id}的所有登录信息')
    except (FileNotFoundError,SystemExit):
        await matcher.finish('你尚未登录，无法删除登录信息')


@fan_once.handle()
async def _(matcher:Matcher,event:MessageEvent):
    data_path = Path().joinpath(f'data/bilifan/{event.user_id}')
    data_path.mkdir(parents=True, exist_ok=True)
    msg_path = Path().joinpath(f'data/bilifan/{event.user_id}/login_info.txt')
    try:
        if msg_path.is_file():
            logger.info(msg_path)
            users = await read_yaml(Path().joinpath('data/bilifan'))
            watchinglive = users.get('WATCHINGLIVE', None)
            await matcher.send(f'开始执行，预计将在{watchinglive}分钟后完成~')
        else:
            logger.info(msg_path)
            await matcher.finish('你尚未登录，请输入【b站登录】')
        messageList = await main(msg_path.parent)
        message_str = '\n'.join(messageList)
        await matcher.finish(message_str)
    except (FileNotFoundError,SystemExit):
        await matcher.finish('你尚未登录，请输入【b站登录】')


@fan_once.handle()
async def _(matcher:Matcher,event:MessageEvent):
    config = load_config()
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
    else:
        group_id = event.user_id
        
    msg_path = Path().joinpath(f'data/bilifan/{event.user_id}/login_info.txt')   
    if msg_path.is_file(): 
        if event.user_id in config:
            await matcher.finish(f'{event.user_id}的定时任务已存在')
        else:
            config[event.user_id] = group_id
            save_config(config)
            users = await read_yaml(Path().joinpath('data/bilifan'))
            cron = users.get('CRON', None)
            try:
                fields = cron.split(" ")
                await matcher.finish(f'已增加{event.user_id}的定时任务，将在每天{fields[0]}时{fields[1]}分开始执行~')
            except AttributeError:
                await matcher.finish('定时格式不正确，无法设置定时任务')
    else:
        await matcher.finish('你尚未登录，请输入【b站登录】')


@del_only.handle()
async def _(matcher:Matcher,event:MessageEvent):
    config = load_config()
    msg_path = Path().joinpath(f'data/bilifan/{event.user_id}/login_info.txt')   
    if msg_path.is_file(): 
        if event.user_id in config:
            del config[event.user_id]
            save_config(config)
            await matcher.finish(f'已删除{event.user_id}的定时任务')
        else:
            await matcher.finish(f'{event.user_id}未设置定时任务')


@del_all.handle()
async def _(matcher:Matcher):
    msg_path = Path().joinpath('data/bilifan/config.yaml')
    os.remove(msg_path)
    matcher.finish('已删除全部定时刷牌子任务')


@driver.on_bot_connect
async def _():
    users = await read_yaml(Path().joinpath('data/bilifan'))
    cron = users.get('CRON', None)
    try:
        fields = cron.split(" ")
    except AttributeError:
        logger.error('定时格式不正确，不启用定时功能')
        return
    scheduler.add_job(auto_cup, "cron", hour=fields[0], minute=fields[1], id="auto_cup")
    
