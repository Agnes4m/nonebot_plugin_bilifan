import asyncio
import itertools
import json
import os
import sys
import warnings
from pathlib import Path

from nonebot.log import logger

from .src import BiliUser

local_path = Path(__file__).parent


log_file = os.path.join(os.path.dirname(__file__), "log/bilifan_{time:YYYY-MM-DD}.log")
log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

logger.remove()
logger.add(sys.stdout, format=log_format, backtrace=True, diagnose=True, level="INFO")

warnings.filterwarnings(
    "ignore",
    message="The localize method is no longer necessary, as this time zone supports the fold attribute",
)

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
            import anyio
            import yaml

            users = yaml.load(
                await anyio.Path(msg_path / "users.yaml").read_text("u8"),
                Loader=yaml.FullLoader,
            )
            # with Path(msg_path / "users.yaml").open(
            #     "r", encoding="utf-8",
            # ) as f:
            #     users = yaml.load(f, Loader=yaml.FullLoader)
        if users.get("WRITE_LOG_FILE"):
            logger.add(
                log_file if users["WRITE_LOG_FILE"] is True else users["WRITE_LOG_FILE"],
                format=log_format,
                backtrace=True,
                diagnose=True,
                rotation="00:00",
                retention="30 days",
                level="DEBUG",
            )
        assert users["ASYNC"] in [0, 1], "ASYNC参数错误"
        assert users["LIKE_CD"] >= 0, "LIKE_CD参数错误"
        # assert users['SHARE_CD'] >= 0, "SHARE_CD参数错误"
        assert users["DANMAKU_CD"] >= 0, "DANMAKU_CD参数错误"
        try:
            assert users["DANMAKU_NUM"] >= 0, "DANMAKU_NUM参数错误"
        except Exception:
            pass
        assert users["DANMAKU_CHECK_LIGHT"] in [0, 1], "DANMAKU_CHECK_LIGHT参数错误"
        assert users["DANMAKU_CHECK_LEVEL"] in [0, 1], "DANMAKU_CHECK_LEVEL参数错误"
        assert users["WATCHINGLIVE"] >= 0, "WATCHINGLIVE参数错误"
        assert users["WEARMEDAL"] in [0, 1], "WEARMEDAL参数错误"
        config = {
            "ASYNC": users["ASYNC"],
            "LIKE_CD": users["LIKE_CD"],
            # "SHARE_CD": users['SHARE_CD'],
            "DANMAKU_CD": users["DANMAKU_CD"],
            "DANMAKU_NUM": users["DANMAKU_NUM"],
            "DANMAKU_CHECK_LIGHT": users["DANMAKU_CHECK_LIGHT"],
            "DANMAKU_CHECK_LEVEL": users["DANMAKU_CHECK_LEVEL"],
            "WATCHINGLIVE": users["WATCHINGLIVE"],
            "WEARMEDAL": users["WEARMEDAL"],
            "SIGNINGROUP": users.get("SIGNINGROUP", 2),
            "LEVEN": users.get("LEVEN", 20),
            "WHACHASYNER": users.get("WHACHASYNER", 1),
            "STOPWATCHINGTIME": None,
        }
        stoptime = users.get("STOPWATCHINGTIME", None)
        if stoptime:
            import time

            now = int(time.time())
            if isinstance(stoptime, int):
                delay = now + int(stoptime)
            else:
                delay = int(
                    time.mktime(
                        time.strptime(
                            f'{time.strftime("%Y-%m-%d", time.localtime(now))} {stoptime}',
                            "%Y-%m-%d %H:%M:%S",
                        )
                    )
                )
                delay = delay if delay > now else delay + 86400
            config["STOPWATCHINGTIME"] = delay
            logger.info(
                f"本轮任务将在 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(config['STOPWATCHINGTIME']))} 结束"
            )
    except Exception as e:
        logger.error(f"读取配置文件失败,请检查配置文件格式是否正确: {e}")
        exit(1)
    return users


@logger.catch
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
            init_tasks.append(bili_user.init())
            start_tasks.append(bili_user.start())
            catch_msg.append(bili_user.sendmsg())

    try:
        await asyncio.gather(*init_tasks)
        await asyncio.gather(*start_tasks)
    except Exception as e:
        logger.exception(e)
        message_list = [f"任务执行失败: {e}"]
    else:
        message_list = []

    try:
        catch_msg_results = await asyncio.gather(*catch_msg)
    except Exception as e:
        logger.exception(e)
        message_list.append(f"发送消息失败: {e}")
    else:
        message_list += list(itertools.chain.from_iterable(catch_msg_results))

    [logger.info(message) for message in message_list]
    return message_list


def run(*args, **kwargs):  # noqa: ARG001
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(mains(Path().joinpath("data/bilifan")))
    logger.info("任务结束，等待下一次执行。")


# if __name__ == '__main__':
# cron = users.get('CRON', None)
# cron = users.get('CRON', None)

# if cron:
#     from apscheduler.schedulers.blocking import BlockingScheduler
#     from apscheduler.triggers.cron import CronTrigger
# if cron:
#     from apscheduler.schedulers.blocking import BlockingScheduler
#     from apscheduler.triggers.cron import CronTrigger

#     logger.info(f'使用内置定时器 {cron}，开启定时任务，等待时间到达后执行。')
#     schedulers = BlockingScheduler()
#     schedulers.add_job(run, CronTrigger.from_crontab(cron), misfire_grace_time=3600)
#     schedulers.start()
# elif "--auto" in sys.argv:
#     from apscheduler.schedulers.blocking import BlockingScheduler
#     from apscheduler.triggers.interval import IntervalTrigger
#     import datetime
#     logger.info(f'使用内置定时器 {cron}，开启定时任务，等待时间到达后执行。')
#     schedulers = BlockingScheduler()
#     schedulers.add_job(run, CronTrigger.from_crontab(cron), misfire_grace_time=3600)
#     schedulers.start()
# elif "--auto" in sys.argv:
#     from apscheduler.schedulers.blocking import BlockingScheduler
#     from apscheduler.triggers.interval import IntervalTrigger
#     import datetime

#     logger.info('使用自动守护模式，每隔 24 小时运行一次。')
#     scheduler = BlockingScheduler(timezone='Asia/Shanghai')
#     scheduler.add_job(
#         run,
#         IntervalTrigger(hours=24),
#         next_run_time=datetime.datetime.now(),
#         misfire_grace_time=3600,
#     )
#     scheduler.start()
# else:
#     logger.info('未配置定时器，开启单次任务。')
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(main())
#     logger.info("任务结束")

#     logger.info('使用自动守护模式，每隔 24 小时运行一次。')
#     scheduler = BlockingScheduler(timezone='Asia/Shanghai')
#     scheduler.add_job(
#         run,
#         IntervalTrigger(hours=24),
#         next_run_time=datetime.datetime.now(),
#         misfire_grace_time=3600,
#     )
#     scheduler.start()
# else:
#     logger.info('未配置定时器，开启单次任务。')
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(main())
#     logger.info("任务结束")
