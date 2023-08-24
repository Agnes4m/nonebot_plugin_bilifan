from pathlib import Path
import yaml
import os
import shutil
import asyncio

from nonebot.log import logger
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import Bot

from .main import main

config_dir = Path('data/bilifan')
config_dir.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = config_dir / 'config.yaml'
if not os.path.exists(Path().joinpath('data/bilifan/users.yaml')):
    logger.info('初始化配置文件')
    shutil.copy2(Path(__file__).parent.joinpath('users.yaml'), Path().joinpath('data/bilifan/users.yaml'))
if not CONFIG_PATH.exists():
    # 创建一个空YAML文件
    with CONFIG_PATH.open('w') as f:
        yaml.dump({}, f)


def load_config():
    if not CONFIG_PATH.exists():
        CONFIG_PATH.touch()
        return {}

    with CONFIG_PATH.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def save_config(data):
    with CONFIG_PATH.open('w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)

async def auto_cup():
    config = load_config()
    count = {}
    tasks = []

    for user_id, group_id in config.items():
        msg_path = Path().joinpath(f'data/bilifan/{user_id}/login_info.txt')
        if msg_path.is_file:
            pass
        else:
            logger.warning('usr_id尚未登录，已忽略')
            continue

        task = asyncio.create_task(main(msg_path.parent))
        tasks.append(task)

    messageList = []
    for task in asyncio.as_completed(tasks):
        messageList.extend(await task)

    message_str = '\n'.join(messageList)

    if count:
        for group_id, num in count.items():
            await get_bot().send_group_msg(group_id=group_id, message=f'今日已完成{num}个自动刷牌子任务')

    if message_str:
        for user_id, group_id in config.items():
            if user_id == group_id:
                await get_bot().send_private_msg(user_id=user_id, message=message_str)
                continue
            else:
                count_value = count.get(group_id, 0)
                count[group_id] = count_value + 1 
                
def render_forward_msg(msg_list: list, uid=2711142767, name='宁宁',bot:Bot = None):
    try:
        uid = bot.self_id
        name = list(bot.config.nickname)[0]
    except Exception as e:
        logger.warning(f'获取bot信息错误\n{e}')
    forward_msg:list = []
    for msg in msg_list:
        forward_msg.append({
            "type": "node",
            "data": {
                "name": str(name),
                "uin": str(uid),
                "content": msg
            }
        })
    return forward_msg