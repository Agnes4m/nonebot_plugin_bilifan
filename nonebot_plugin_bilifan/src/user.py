import asyncio
import time
import uuid
from datetime import datetime, timedelta

from aiohttp import ClientSession, ClientTimeout
from loguru import logger
from nonebot.log import logger as log

global user


class BiliUser:
    def __init__(
        self,
        access_token: str,
        whiteUIDs: str = "",
        bannedUIDs: str = "",
        config: dict = {},  # noqa: B006
    ):
        from .api import BiliApi

        self.mid, self.name = 0, ""
        self.access_key = access_token  # 登录凭证
        try:
            self.whiteList = [
                int(x if x else 0) for x in str(whiteUIDs).split(",")
            ]  # 白名单UID
            self.bannedList = [
                int(x if x else 0) for x in str(bannedUIDs).split(",")
            ]  # 黑名单
        except ValueError:
            raise ValueError("白名单或黑名单格式错误")  # noqa: B904

        self.config = config
        self.medals = []  # 用户所有勋章
        self.medalsNeedDo = []  # 用户所有勋章，等级小于20的 未满1500的

        self.session = ClientSession(timeout=ClientTimeout(total=3))
        self.api = BiliApi(self, self.session)

        self.retryTimes = 0  # 任务重试次数
        self.maxRetryTimes = 10  # 最大重试次数
        self.message = []
        self.errmsg = ["错误日志："]
        self.uuids = [str(uuid.uuid4()) for _ in range(2)]

    async def loginVerify(self) -> bool:
        """
        登录验证
        """
        loginInfo = await self.api.loginVerift()
        self.mid, self.name = loginInfo["mid"], loginInfo["name"]
        self.log = logger.info(f"b站名称：{self.name}")
        if loginInfo["mid"] == 0:
            self.isLogin = False
            return False
        userInfo = await self.api.getUserInfo()
        if userInfo["medal"]:
            medalInfo = await self.api.getMedalsInfoByUid(userInfo["medal"]["target_id"])
            if medalInfo["has_fans_medal"]:
                self.initialMedal = medalInfo["my_fans_medal"]
        self.log = logger.success(str(loginInfo["mid"]) + " 登录成功")
        self.isLogin = True
        return True

    async def doSign(self):
        try:
            signInfo = await self.api.doSign()
            log.success(
                "签到成功,本月签到次数: {}/{}".format(
                    signInfo["hadSignDays"],
                    signInfo["allDays"],
                ),
            )
            self.message.append(
                f"【{self.name}】 签到成功,本月签到次数: {signInfo['hadSignDays']}/{signInfo['allDays']}",
            )
        except Exception as e:
            log.error(e)
            self.errmsg.append(f"【{self.name}】" + str(e))
        userInfo = await self.api.getUserInfo()
        log.info(
            "当前用户UL等级: {} ,还差 {} 经验升级".format(
                userInfo["exp"]["user_level"],
                userInfo["exp"]["unext"],
            ),
        )
        self.message.append(
            f"【{self.name}】 UL等级: {userInfo['exp']['user_level']} ,还差 {userInfo['exp']['unext']} 经验升级",
        )

    async def getMedals(self):
        """
        获取用户勋章
        """
        self.medals.clear()
        self.medalsNeedDo.clear()
        async for medal in self.api.getFansMedalandRoomID():  # type: ignore
            if self.whiteList == [0]:
                if medal["medal"]["target_id"] in self.bannedList:
                    log.warning(
                        f"{medal['anchor_info']['nick_name']} 在黑名单中，已过滤",
                    )
                    continue
                self.medals.append(medal) if medal["room_info"]["room_id"] != 0 else ...
            else:
                if medal["medal"]["target_id"] in self.whiteList:
                    (
                        self.medals.append(medal)
                        if medal["room_info"]["room_id"] != 0
                        else ...
                    )
                    log.success(
                        f"{medal['anchor_info']['nick_name']} 在白名单中，加入任务",
                    )
        [
            self.medalsNeedDo.append(medal)
            for medal in self.medals
            if medal["medal"]["level"] < self.config["LEVEN"]
            and medal["medal"]["today_feed"] < 200
        ]

    async def like_v3(self, failedMedals: list = []):  # noqa: B006
        if self.config["LIKE_CD"] == 0:
            log.info("点赞任务已关闭")
            return
        try:
            if not failedMedals:
                failedMedals = self.medals
            if not self.config["ASYNC"]:
                log.info("同步点赞任务开始....")
                for index, medal in enumerate(failedMedals):
                    i = 0
                    for i in range(30):
                        tasks = []
                        (
                            tasks.append(
                                self.api.likeInteractV3(
                                    medal["room_info"]["room_id"],
                                    medal["medal"]["target_id"],
                                    self.mid,
                                )
                            )
                            if self.config["LIKE_CD"]
                            else ...
                        )
                        await asyncio.gather(*tasks)
                        await asyncio.sleep(self.config["LIKE_CD"])
                    log.success(
                        f"{medal['anchor_info']['nick_name']} 点赞{i+1}次成功 {index+1}/{len(self.medals)}",
                    )
            else:
                log.info("异步点赞任务开始....")
                for i in range(35):
                    allTasks = []
                    medal = {}
                    for medal in failedMedals:
                        (
                            allTasks.append(
                                self.api.likeInteractV3(
                                    medal["room_info"]["room_id"],
                                    medal["medal"]["target_id"],
                                    self.mid,
                                )
                            )
                            if self.config["LIKE_CD"]
                            else ...
                        )
                    await asyncio.gather(*allTasks)
                    log.success(
                        f"{medal['anchor_info']['nick_name']} 异步点赞{i+1}次成功",
                    )
                    await asyncio.sleep(self.config["LIKE_CD"])

            await asyncio.sleep(10)
            log.success("点赞任务完成")
            # finallyMedals = [
            #     medal
            #     for medal in self.medals
            #     if medal["medal"]["today_feed"] >= 100
            # ]
            # msg = "20级以下牌子共 {} 个,完成点赞任务 {} 个".format(
            #     len(self.medals),
            #     len(finallyMedals),
            # )
            # log.info(msg)
        except Exception:
            log.exception("点赞任务异常")
            self.errmsg.append(f"【{self.name}】 点赞任务异常,请检查日志")

    async def sendDanmaku(self):
        """
        每日弹幕打卡
        """
        if not self.config["DANMAKU_CD"]:
            log.info("弹幕任务关闭")
            return
        # 计算实际执行的长度
        filtered_medals = [
            medal
            for medal in self.medals
            if not (
                self.config["DANMAKU_CHECK_LIGHT"] and medal["medal"]["is_lighted"] == 1
            )
            and not (
                not self.config["DANMAKU_CHECK_LEVEL"]
                and medal["medal"]["level"] > self.config["LEVEN"]
            )
        ]
        filtered_medals_length = len(filtered_medals)
        log.info(
            "弹幕打卡任务开始....(预计 {} 秒完成)".format(
                filtered_medals_length
                * self.config["DANMAKU_CD"]
                * self.config["DANMAKU_NUM"]
            ),
        )
        n = 0
        successnum = 0
        for medal in self.medals:
            n += 1
            if self.config["DANMAKU_CHECK_LIGHT"] and medal["medal"]["is_lighted"] == 1:
                log.info(
                    "{} 房间已点亮，跳过".format(medal["anchor_info"]["nick_name"]),
                )
                continue
            if (
                not self.config["DANMAKU_CHECK_LEVEL"]
                and medal["medal"]["level"] > self.config["LEVEN"]
            ):
                log.info(
                    "{} 房间已满级，跳过".format(medal["anchor_info"]["nick_name"]),
                )
                continue
            (
                (await self.api.wearMedal(medal["medal"]["medal_id"]))
                if self.config["WEARMEDAL"]
                else ...
            )
            for i in range(self.config["DANMAKU_NUM"]):
                try:
                    danmaku = await self.api.sendDanmaku(medal["room_info"]["room_id"])
                    log.info(
                        "{} 房间弹幕打卡({}/{})成功: {} ({}/{})".format(
                            medal["anchor_info"]["nick_name"],
                            i + 1,
                            self.config["DANMAKU_NUM"],
                            danmaku,
                            n,
                            len(self.medals),
                        ),
                    )
                except Exception as e:
                    log.error(
                        "{} 房间弹幕打卡({}/{})失败: {}".format(
                            medal["anchor_info"]["nick_name"],
                            i,
                            self.config["DANMAKU_NUM"],
                            e,
                        ),
                    )
                    self.errmsg.append(
                        f"【{self.name}】 {medal['anchor_info']['nick_name']} 房间弹幕打卡失败: {str(e)}"
                    )
                finally:
                    await asyncio.sleep(self.config["DANMAKU_CD"])
            successnum += 1

        if hasattr(self, "initialMedal"):
            (
                (await self.api.wearMedal(self.initialMedal["medal_id"]))
                if self.config["WEARMEDAL"]
                else ...
            )
        log.success("弹幕打卡任务完成")
        self.message.append(
            f"【{self.name}】 弹幕打卡任务完成 {successnum}/{filtered_medals_length}/{len(self.medals)}"
        )

    async def init(self):
        if not await self.loginVerify():
            log.error(f"登录失败 可能是 access_key：{self.access_key} 过期 , 请重新获取")
            self.errmsg.append("登录失败 可能是登录已过期 , 请发送【b站登录】重新登录")
            await self.session.close()
        else:
            # await self.doSign()
            await self.getMedals()

    async def start(self):
        if self.isLogin:
            tasks = []
            if self.medalsNeedDo:
                log.info(f"共有 {len(self.medalsNeedDo)} 个牌子未满 1500 亲密度")
                tasks.append(self.like_v3())
                tasks.append(self.watchinglive())
            else:
                log.info("所有牌子已满 1500 亲密度")
            tasks.append(self.sendDanmaku())
            tasks.append(self.signInGroups())
            await asyncio.gather(*tasks)

    async def sendmsg(self):
        if not self.isLogin:
            await self.session.close()
            return self.message + self.errmsg
        await self.getMedals()
        nameList1, nameList2, nameList3, nameList4 = [], [], [], []
        for medal in self.medals:
            if medal["medal"]["level"] >= self.config["LEVEN"]:
                continue
            today_feed = medal["medal"]["today_feed"]
            nick_name = medal["anchor_info"]["nick_name"]
            if today_feed >= 1500:
                nameList1.append(nick_name)
            elif 1200 < today_feed <= 1500:
                nameList2.append(nick_name)
            elif 300 < today_feed <= 1200:
                nameList3.append(nick_name)
            elif today_feed <= 300:
                nameList4.append(nick_name)
        self.message.append(f"【{self.name}】 今日亲密度获取情况如下（20级以下）：")

        for l, n in zip(  # noqa: E741
            [nameList1, nameList2, nameList3, nameList4],
            ["【1500】", "【1200至1500】", "【300至1200】", "【300以下】"],
        ):
            if len(l) > 0:
                self.message.append(
                    f"{n}{' '.join(l[:5])}{'等' if len(l) > 5 else ''} {len(l)}个"
                )

        if hasattr(self, "initialMedal"):
            initialMedalInfo = await self.api.getMedalsInfoByUid(
                self.initialMedal["target_id"]
            )
            if initialMedalInfo["has_fans_medal"]:
                initialMedal = initialMedalInfo["my_fans_medal"]
                self.message.append(
                    f"【当前佩戴】「{initialMedal['medal_name']}」({initialMedal['target_name']}) {initialMedal['level']} 级 "
                )
                if (
                    initialMedal["level"] < self.config["LEVEN"]
                    and initialMedal["today_feed"] != 0
                ):
                    need = initialMedal["next_intimacy"] - initialMedal["intimacy"]
                    need_days = need // 1500 + 1
                    end_date = datetime.now() + timedelta(days=need_days)
                    self.message.append(
                        f"今日已获取亲密度 {initialMedal['today_feed']} (B站结算有延迟，请耐心等待)"
                    )
                    self.message.append(
                        f"距离下一级还需 {need} 亲密度 预计需要 {need_days} 天 ({end_date.strftime('%Y-%m-%d')},以每日 1500 亲密度计算)"
                    )
        await self.session.close()
        return self.message + self.errmsg + ["---"]

    async def watchinglive(self):
        if not self.config["WATCHINGLIVE"]:
            log.info("每日观看直播任务关闭")
            return
        HEART_MAX = self.config["WATCHINGLIVE"]
        log.info(f"每日{HEART_MAX}分钟任务开始")
        n = 0
        for medal in self.medalsNeedDo:
            n += 1
            for heartNum in range(1, HEART_MAX + 1):
                if self.config["STOPWATCHINGTIME"]:
                    if int(time.time()) >= self.config["STOPWATCHINGTIME"]:
                        self.log.log("INFO", "已到设置的时间，自动停止直播任务")
                        return
                tasks = []
                tasks.append(
                    self.api.heartbeat(
                        medal["room_info"]["room_id"], medal["medal"]["target_id"]
                    )
                )
                await asyncio.gather(*tasks)
                if heartNum % 5 == 0:
                    log.info(
                        f"{medal['anchor_info']['nick_name']} 第{heartNum}次心跳包已发送（{n}/{len(self.medalsNeedDo)}）",
                    )
                await asyncio.sleep(60)
            log.success(f"每日{HEART_MAX}分钟任务完成")

    async def signInGroups(self):
        if not self.config["SIGNINGROUP"]:
            log.info("应援团签到任务关闭")
            return
        log.info("应援团签到任务开始")
        try:
            n = 0
            async for group in self.api.getGroups():
                if group["owner_uid"] == self.mid:
                    continue
                try:
                    await self.api.signInGroups(group["group_id"], group["owner_uid"])
                except Exception as e:
                    log.error(group["group_name"] + " 签到失败")
                    self.errmsg.append(f"应援团签到失败: {e}")
                    continue
                log.debug(group["group_name"] + " 签到成功")
                await asyncio.sleep(self.config["SIGNINGROUP"])
                n += 1
            if n:
                log.success(f"应援团签到任务完成 {n}/{n}")
                self.message.append(f" 应援团签到任务完成 {n}/{n}")
            else:
                log.warning("没有加入应援团")
        except Exception as e:
            log.exception(e)
            log.error("应援团签到任务失败: " + str(e))
            self.errmsg.append("应援团签到任务失败: " + str(e))
