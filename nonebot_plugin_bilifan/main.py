import asyncio
import itertools
import json
import os
import warnings
from pathlib import Path

from nonebot.log import logger
from nonebot.log import logger as log

from .src import BiliUser

local_path = Path(__file__).parent

__VERSION__ = "0.3.6"

warnings.filterwarnings(
    "ignore",
    message="The localize method is no longer necessary, as this time zone supports the fold attribute",
)
# os.chdir(os.path.dirname(os.path.abspath(__file__)).split(__file__)[0])

base_path = Path().joinpath("data/bilifan")
base_path = Path().joinpath("data/bilifan")
base_path.mkdir(parents=True, exist_ok=True)
logger.info(base_path)

global users


async def read_yaml(msg_path: Path):
    global config, users
    try:
        if os.environ.get("USERS"):
            users = json.loads(os.environ.get("USERS"))  # type: ignore
        else:
            import yaml

            with Path(msg_path / "users.yaml").open("r", encoding="utf-8") as f:
                users = yaml.load(f, Loader=yaml.FullLoader)
        assert users["ASYNC"] in [0, 1], "ASYNC参数错误"
        assert users["LIKE_CD"] >= 0, "LIKE_CD参数错误"
        assert users["ASYNC"] in [0, 1], "ASYNC参数错误"
        assert users["LIKE_CD"] >= 0, "LIKE_CD参数错误"
        # assert users['SHARE_CD'] >= 0, "SHARE_CD参数错误"
        assert users["DANMAKU_CD"] >= 0, "DANMAKU_CD参数错误"
        assert users["WATCHINGLIVE"] >= 0, "WATCHINGLIVE参数错误"
        assert users["WEARMEDAL"] in [0, 1], "WEARMEDAL参数错误"
        assert users["DANMAKU_CD"] >= 0, "DANMAKU_CD参数错误"
        assert users["WATCHINGLIVE"] >= 0, "WATCHINGLIVE参数错误"
        assert users["WEARMEDAL"] in [0, 1], "WEARMEDAL参数错误"
        config = {
            "ASYNC": users["ASYNC"],
            "LIKE_CD": users["LIKE_CD"],
            "ASYNC": users["ASYNC"],
            "LIKE_CD": users["LIKE_CD"],
            # "SHARE_CD": users['SHARE_CD'],
            "DANMAKU_CD": users["DANMAKU_CD"],
            "WATCHINGLIVE": users["WATCHINGLIVE"],
            "WEARMEDAL": users["WEARMEDAL"],
            "SIGNINGROUP": users.get("SIGNINGROUP", 2),
            "DANMAKU_CD": users["DANMAKU_CD"],
            "WATCHINGLIVE": users["WATCHINGLIVE"],
            "WEARMEDAL": users["WEARMEDAL"],
            "SIGNINGROUP": users.get("SIGNINGROUP", 2),
        }
    except Exception as e:
        log.error(f"读取配置文件失败,请检查配置文件格式是否正确: {e}")
        exit(1)
    return users


@log.catch
async def mains(msg_path):
    await read_yaml(msg_path)
    init_tasks = []
    start_tasks = []
    catch_msg = []

    for user in users["USERS"]:
        if user["access_key"]:
            bili_user = BiliUser(
                user["access_key"],
                user.get("white_uid", ""),
                user.get("banned_uid", ""),
                config,
            )
    for user in users["USERS"]:
        if user["access_key"]:
            bili_user = BiliUser(
                user["access_key"],
                user.get("white_uid", ""),
                user.get("banned_uid", ""),
                config,
            )
            init_tasks.append(bili_user.init())
            start_tasks.append(bili_user.start())
            catch_msg.append(bili_user.sendmsg())

    try:
        await asyncio.gather(*init_tasks)
        await asyncio.gather(*start_tasks)
    except Exception as e:
        log.exception(e)
        message_list = [f"任务执行失败: {e}"]
    else:
        message_list = []

    try:
        catch_msg_results = await asyncio.gather(*catch_msg)
    except Exception as e:
        log.exception(e)
        message_list.append(f"发送消息失败: {e}")
    else:
        message_list += list(itertools.chain.from_iterable(catch_msg_results))

    [log.info(message) for message in message_list]
    return message_list


def run(*args, **kwargs):  # noqa: ARG001
    loop = asyncio.new_event_loop()
    loop.run_until_complete(mains(Path().joinpath("data/bilifan")))
    log.info("任务结束，等待下一次执行。")


# if __name__ == '__main__':
# cron = users.get('CRON', None)
# cron = users.get('CRON', None)

# if cron:
#     from apscheduler.schedulers.blocking import BlockingScheduler
#     from apscheduler.triggers.cron import CronTrigger
# if cron:
#     from apscheduler.schedulers.blocking import BlockingScheduler
#     from apscheduler.triggers.cron import CronTrigger

#     log.info(f'使用内置定时器 {cron}，开启定时任务，等待时间到达后执行。')
#     schedulers = BlockingScheduler()
#     schedulers.add_job(run, CronTrigger.from_crontab(cron), misfire_grace_time=3600)
#     schedulers.start()
# elif "--auto" in sys.argv:
#     from apscheduler.schedulers.blocking import BlockingScheduler
#     from apscheduler.triggers.interval import IntervalTrigger
#     import datetime
#     log.info(f'使用内置定时器 {cron}，开启定时任务，等待时间到达后执行。')
#     schedulers = BlockingScheduler()
#     schedulers.add_job(run, CronTrigger.from_crontab(cron), misfire_grace_time=3600)
#     schedulers.start()
# elif "--auto" in sys.argv:
#     from apscheduler.schedulers.blocking import BlockingScheduler
#     from apscheduler.triggers.interval import IntervalTrigger
#     import datetime

#     log.info('使用自动守护模式，每隔 24 小时运行一次。')
#     scheduler = BlockingScheduler(timezone='Asia/Shanghai')
#     scheduler.add_job(
#         run,
#         IntervalTrigger(hours=24),
#         next_run_time=datetime.datetime.now(),
#         misfire_grace_time=3600,
#     )
#     scheduler.start()
# else:
#     log.info('未配置定时器，开启单次任务。')
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(main())
#     log.info("任务结束")

#     log.info('使用自动守护模式，每隔 24 小时运行一次。')
#     scheduler = BlockingScheduler(timezone='Asia/Shanghai')
#     scheduler.add_job(
#         run,
#         IntervalTrigger(hours=24),
#         next_run_time=datetime.datetime.now(),
#         misfire_grace_time=3600,
#     )
#     scheduler.start()
# else:
#     log.info('未配置定时器，开启单次任务。')
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(main())
#     log.info("任务结束")
