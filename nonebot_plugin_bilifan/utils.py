import asyncio
import shutil
from pathlib import Path

import yaml
from nonebot import get_bot

# from nonebot.adapters import Bot
from nonebot.log import logger

from .main import mains

config_dir = Path("data/bilifan")
config_dir.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = config_dir / "config.yaml"
if not Path().joinpath("data/bilifan/users.yaml").is_file():
    logger.info("初始化配置文件")
    shutil.copy2(
        Path(__file__).parent.joinpath("users.yaml"),
        Path().joinpath("data/bilifan/users.yaml"),
    )
if not CONFIG_PATH.exists():
    # 创建一个空YAML文件
    with CONFIG_PATH.open("w") as f:
        yaml.dump({}, f)


def load_config():
    if not CONFIG_PATH.exists():
        CONFIG_PATH.touch()
        return {}

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_config(data):
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)


async def auto_cup():
    config = load_config()
    count: dict = {}
    tasks = []

    for user_id, group_id in config.items():  # noqa: B007
        msg_path = Path(f"data/bilifan/{user_id}/login_info.txt")
        if msg_path.is_file():
            task = asyncio.create_task(mains(msg_path.parent))
            tasks.append((user_id, group_id, task))
        else:
            logger.warning(f"{user_id}尚未登录，已忽略")

    messageList = []
    for user_id, group_id, task in tasks:
        message = await task
        messageList.append((user_id, group_id, message))

    for user_id, group_id, message in messageList:
        messageStr = "\n".join(message)
        logger.info(f"{user_id}用户自动刷牌子任务执行完成，{messageStr}")
        if group_id.startswith("group"):
            group_num = group_id.split("_")[1]
            if group_num in count:
                count[group_num] += 1
            else:
                count[group_num] = 1
        elif user_id != group_id:
            if group_id in count:
                count[group_id] += 1
            else:
                count[group_id] = 1
        await get_bot().send_private_msg(user_id=user_id, message=messageStr)

    for group_num, num in count.items():
        logger.info(f"{group_num}群组自动刷牌子任务执行完成，共{num}个")
        await get_bot().send_group_msg(
            group_id=group_num,
            message=f"本群今日已完成{num}个自动刷牌子任务",
        )


def render_forward_msg(msg_list: list, uid=2711142767, name="宁宁"):
    try:
        uid = get_bot().self_id
        name = next(iter(get_bot().config.nickname))
    except Exception as e:
        logger.warning(f"获取bot信息错误\n{e}")
    forward_msg = []
    for msg in msg_list:
        forward_msg.append(
            {
                "type": "node",
                "data": {"name": str(name), "uin": str(uid), "content": msg},
            },
        )
    return forward_msg
