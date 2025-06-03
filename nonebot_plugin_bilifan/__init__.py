import shutil
from pathlib import Path
from typing import List

# import aiohttp
from nonebot import get_driver, on_command, require
from nonebot.adapters import Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from .login import draw_QR, get_tv_qrcode_url_and_auth_code, verify_login
from .main import mains, read_yaml
from .src import BiliUser  # noqa: F401
from .utils import auto_cup, load_config, save_config

try:
    require("nonebot_plugin_apscheduler")
    from nonebot_plugin_apscheduler import scheduler
except BaseException:
    scheduler = None
require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import UniMessage  # noqa: E402

logger.opt(colors=True).info(
    (
        "已检测到软依赖<y>nonebot_plugin_apscheduler</y>, <g>开启定时任务功能</g>"
        if scheduler
        else "未检测到软依赖<y>nonebot_plugin_apscheduler</y>，<r>禁用定时任务功能</r>"
    ),
)


driver = get_driver()
__version__ = "0.4.4"
__plugin_meta__ = PluginMetadata(
    name="bilifan",
    description="b站粉丝牌~",
    usage="发送 开始刷牌子 即可",
    type="application",
    homepage="https://github.com/Agnes4m/nonebot_plugin_bilifan",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
    extra={
        "version": __version__,
        "author": "Agnes4m <Z735803792@163.com>",
    },
)

login_in = on_command("blogin", aliases={"b站登录"}, block=False)
login_del = on_command("blogin_del", aliases={"删除登录信息"}, block=False)
fan_once = on_command("bfan", aliases={"开始刷牌子", "开始粉丝牌"}, block=False)
fan_auto = on_command(
    "addfan",
    aliases={"自动刷牌子", "自动粉丝牌"},
    priority=40,
    block=False,
)
del_only = on_command("bdel", aliases={"取消自动刷牌子", "取消自动粉丝牌"}, block=False)
del_all = on_command(
    "bdel_all",
    aliases={"删除全部定时任务"},
    block=False,
    permission=SUPERUSER,
)
del_config = on_command(
    "bdel_config",
    aliases={"b站删除配置"},
    block=False,
    permission=SUPERUSER,
)


@login_in.handle()
async def _(matcher: Matcher, event: Event):
    try:
        login_url, auth_code = await get_tv_qrcode_url_and_auth_code()
    except Exception as e:
        print(e)
        await matcher.finish("已超时，请稍后重试！")
    data_path = Path().joinpath(f"data/bilifan/{event.get_user_id()}")
    data_path.mkdir(parents=True, exist_ok=True)
    data = await draw_QR(login_url)
    forward_msg = "本功能会调用并保存b站登录信息的cookie,请确保你在信任本机器人主人的情况下登录,如果出现财产损失,本作者对此不负责任"
    try:
        # if isinstance(event, GroupEvent):
        #     await bot.call_api(
        #         "send_group_forward_msg", group_id=event.group_id, messages=forward_msg
        #     )
        # else:
        await UniMessage.text(forward_msg).send()
        await UniMessage.image(raw=data).send()
    except Exception:
        logger.warning("二维码可能被风控，发送链接")
        await matcher.send("将此链接复制到手机B站打开:" + login_url)
    while True:
        a = await verify_login(auth_code, data_path)
        if a:
            await matcher.send(f"登录成功！\nqq:{event.get_user_id()}\n{a}")
            break
        await matcher.finish("登录失败！")


@login_del.handle()
async def _(matcher: Matcher, event: Event):
    config = load_config()
    msg_path = Path().joinpath(f"data/bilifan/{event.get_user_id()}/login_info.txt")
    if msg_path.is_file() and event.get_user_id() in config:
        del config[event.get_user_id()]
        save_config(config)
        logger.info(f"已删除{event.get_user_id()}的定时任务")
    try:
        data_path = Path().joinpath(f"data/bilifan/{event.get_user_id()}")
        shutil.rmtree(data_path)
        await matcher.finish(f"已删除{event.get_user_id()}的所有登录信息")
    except (FileNotFoundError, SystemExit):
        await matcher.finish("你尚未登录，无法删除登录信息")


@fan_once.handle()
async def _(matcher: Matcher, event: Event):
    data_path = Path().joinpath(f"data/bilifan/{event.get_user_id()}")
    data_path.mkdir(parents=True, exist_ok=True)
    msg_path = Path().joinpath(f"data/bilifan/{event.get_user_id()}/login_info.txt")
    try:
        if msg_path.is_file():
            logger.info(msg_path)
            users = await read_yaml(Path().joinpath("data/bilifan"))
            watchinglive: int = users.get("WATCHINGLIVE", None)
            await matcher.send(f"开始执行，预计将在粉丝牌数量*{watchinglive}分钟后完成~")
        else:
            logger.info(msg_path)
            await matcher.finish("你尚未登录，请输入【b站登录】")
        messageList: List[str] = await mains(msg_path.parent)
        message_str = "\n".join(messageList)
        await matcher.finish(message_str)
    except (FileNotFoundError, SystemExit):
        await matcher.finish("你尚未登录，请输入【b站登录】")


@fan_auto.handle()
async def _(matcher: Matcher, event: Event):
    config = load_config()
    group_id = event.get_session_id()

    msg_path = Path().joinpath(f"data/bilifan/{event.get_user_id()}/login_info.txt")
    if msg_path.is_file():
        if event.get_user_id() in config:
            users = await read_yaml(Path().joinpath("data/bilifan"))
            cron = users.get("CRON", None)
            try:
                fields = cron.split(" ")
                await matcher.finish(
                    f"{event.get_user_id()}的定时任务已存在，将在每天{fields[1]}时{fields[0]}分后开始执行~",
                )
            except AttributeError:
                await matcher.finish("定时格式不正确，请删除定时任务后重新设置")
        else:
            config[event.get_user_id()] = group_id
            save_config(config)
            users = await read_yaml(Path().joinpath("data/bilifan"))
            cron = users.get("CRON", None)
            try:
                fields = cron.split(" ")
                await matcher.finish(
                    f"已增加{event.get_user_id()}的定时任务，将在每天{fields[1]}时{fields[0]}分后开始执行~",
                )
            except AttributeError:
                await matcher.finish("定时格式不正确，无法设置定时任务")
    else:
        await matcher.finish("你尚未登录，请输入【b站登录】")


@del_only.handle()
async def _(matcher: Matcher, event: Event):
    config = load_config()
    msg_path = Path().joinpath(f"data/bilifan/{event.get_user_id()}/login_info.txt")
    if msg_path.is_file():
        if event.get_user_id() in config:
            del config[event.get_user_id()]
            save_config(config)
            await matcher.finish(f"已删除{event.get_user_id()}的定时任务")
        else:
            await matcher.finish(f"{event.get_user_id()}未设置定时任务")


@del_all.handle()
async def _(matcher: Matcher):
    msg_path = Path().joinpath("data/bilifan/config.yaml")
    msg_path.unlink()
    await matcher.finish("已删除全部定时刷牌子任务")


@driver.on_bot_connect
async def _():
    users = await read_yaml(Path().joinpath("data/bilifan"))
    cron = users.get("CRON", None)
    try:
        fields = cron.split(" ")
    except AttributeError:
        logger.error("定时格式不正确，不启用定时功能")
        return
    if scheduler is None:
        logger.error("定时格式不正确，不启用定时功能")
        return
    try:
        logger.info(f"定时任务已配置，将在每天{fields[1]}时{fields[0]}分后自动执行~")
        scheduler.add_job(
            auto_cup,
            "cron",
            hour=fields[1],
            minute=fields[0],
            id="auto_cup",
        )
    except Exception:
        logger.warning("定时任务已存在")


@del_config.handle()
async def _(matcher: Matcher, event: Event):
    """删除配置文件"""
    folder_path = Path().joinpath("data/bilifan")
    if folder_path.exists():
        # 删除文件夹及其所有内容
        shutil.rmtree(folder_path)
        print(f"已删除文件夹: {folder_path}")
    else:
        print(f"文件夹不存在: {folder_path}")
