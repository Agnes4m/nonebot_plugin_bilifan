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
__version__ = "0.5.0"
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
update_config = on_command(
    "bupdate_config",
    aliases={"b站更新配置", "更新插件配置"},
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
        logger.error("定时任务未启用，不启用定时功能")
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


@update_config.handle()
async def _(matcher: Matcher, event: Event):
    """批量更新历史配置文件"""
    import shutil

    import anyio
    import yaml

    base_path = Path().joinpath("data/bilifan")
    if not base_path.exists():
        await matcher.finish("配置目录不存在")

    # 1. 首先更新全局模板文件 data/bilifan/users.yaml
    global_template_path = base_path / "users.yaml"
    plugin_template_path = Path(__file__).parent / "users.yaml"

    try:
        # 读取原有的全局模板（保存用户修改的值）
        old_global_config = None
        if global_template_path.exists():
            backup_path = base_path / "users.yaml.bak"
            shutil.copy2(global_template_path, backup_path)
            logger.info(f"已备份全局模板到: {backup_path}")

            old_global_config = yaml.safe_load(
                await anyio.Path(global_template_path).read_text("u8"),
            )

        # 读取插件目录的最新模板
        new_template_config = yaml.safe_load(
            await anyio.Path(plugin_template_path).read_text("u8"),
        )

        # 合并配置：使用新模板的结构，但保留旧模板中用户修改的值
        if old_global_config:
            for field in new_template_config:
                if field == "USERS":
                    continue  # USERS字段使用新模板的结构
                # 如果旧配置中存在该字段，保留旧值
                if field in old_global_config:
                    new_template_config[field] = old_global_config[field]

        # 保存合并后的配置到全局模板（保留用户修改的值）
        yaml_string = yaml.dump(
            new_template_config,
            allow_unicode=True,
            default_flow_style=False,
        )
        await anyio.Path(global_template_path).write_text(yaml_string, "u8")
        logger.success(f"已更新全局模板文件: {global_template_path}")
        messages = ["✓ 已更新全局模板文件（保留原有配置值）"]

        # 使用合并后的配置作为模板
        template_config = new_template_config
    except Exception as e:
        await matcher.finish(f"更新全局模板文件失败: {e}")

    updated_count = 0
    error_count = 0

    updated_count = 0
    error_count = 0

    # 3. 遍历所有用户目录，更新用户配置
    for user_dir in base_path.iterdir():
        if not user_dir.is_dir() or user_dir.name == "__pycache__":
            continue

        config_file = user_dir / "users.yaml"
        if not config_file.exists():
            continue

        try:
            # 读取配置文件
            config = yaml.safe_load(
                await anyio.Path(config_file).read_text("u8"),
            )

            if not config:
                continue

            updated = False

            # 更新用户配置字段（智能合并：只添加缺失字段）
            if (
                "USERS" in config
                and config["USERS"]
                and "USERS" in template_config
                and template_config["USERS"]
            ):
                template_user = (
                    template_config["USERS"][0] if template_config["USERS"] else {}
                )

                for user in config["USERS"]:
                    if not user:
                        continue

                    # 从模板中添加缺失的用户字段
                    for field, default_value in template_user.items():
                        if field not in user:
                            user[field] = default_value
                            updated = True

            # 更新全局配置参数（强制覆盖）
            for field in template_config:
                if field == "USERS":
                    continue
                # 强制覆盖全局配置参数
                if config.get(field) != template_config[field]:
                    config[field] = template_config[field]
                    updated = True

            # 保存配置文件
            if updated:
                yaml_string = yaml.dump(
                    config,
                    allow_unicode=True,
                    default_flow_style=False,
                )
                await anyio.Path(config_file).write_text(yaml_string, "u8")
                updated_count += 1
                messages.append(f"✓ 已更新: {user_dir.name}")
                logger.info(f"已更新配置文件: {config_file}")
            else:
                messages.append(f"○ 无需更新: {user_dir.name}")

        except Exception as e:
            error_count += 1
            messages.append(f"✗ 更新失败: {user_dir.name} - {str(e)}")
            logger.error(f"更新配置文件失败: {config_file}, 错误: {e}")

    # 生成结果消息
    result_msg = f"批量更新完成！\n成功: {updated_count} 个\n失败: {error_count} 个\n"

    if messages:
        result_msg += "\n详细信息:\n" + "\n".join(messages[:10])
        if len(messages) > 10:
            result_msg += f"\n... 还有 {len(messages) - 10} 条"

    await matcher.finish(result_msg)
