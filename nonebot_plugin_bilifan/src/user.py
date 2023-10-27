import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional

from aiohttp import ClientSession, ClientTimeout
from loguru import logger
from nonebot.log import logger as log

# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# logger.remove()
# logger.add(
# sys.stdout,
# colorize=True,
# format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <blue> {extra[user]} </blue> <level>{message}</level>",
# backtrace=True,
# diagnose=True,
# )

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
            raise ValueError("白名单或黑名单格式错误")  # noqa: TRY200, B904
        self.config = config
        self.medals = []  # 用户所有勋章
        self.medalsNeedDo = []  # 用户所有勋章，等级小于20的 未满1500的

        self.session = ClientSession(timeout=ClientTimeout(total=3))
        self.api = BiliApi(self, self.session)

        self.retryTimes = 0  # 点赞任务重试次数
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
        # self.log = logger.info(user=self.name)
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
                "签到成功,本月签到次数: {}/{}".format(signInfo["hadSignDays"], signInfo["allDays"])
            )
            self.message.append(
                f"【{self.name}】 签到成功,本月签到次数: {signInfo['hadSignDays']}/{signInfo['allDays']}"
            )
        except Exception as e:
            log.error(e)
            self.errmsg.append(f"【{self.name}】" + str(e))
        userInfo = await self.api.getUserInfo()
        log.info(
            "当前用户UL等级: {} ,还差 {} 经验升级".format(
                userInfo["exp"]["user_level"], userInfo["exp"]["unext"]
            )
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
                    log.warning(f"{medal['anchor_info']['nick_name']} 在黑名单中，已过滤")
                    continue
                self.medals.append(medal) if medal["room_info"]["room_id"] != 0 else ...
            else:
                if medal["medal"]["target_id"] in self.whiteList:
                    self.medals.append(medal) if medal["room_info"][
                        "room_id"
                    ] != 0 else ...
                    log.success(f"{medal['anchor_info']['nick_name']} 在白名单中，加入任务")
        [
            self.medalsNeedDo.append(medal)
            for medal in self.medals
            if medal["medal"]["level"] < 20 and medal["medal"]["today_feed"] < 1500
        ]

    async def asynclikeandShare(self, failedMedals: list = []):  # noqa: B006
        """
        点赞 、 分享
        """
        if self.config["LIKE_CD"] == 0:
            log.info("点赞任务已关闭")
        elif self.config["SHARE_CD"] == 0:
            log.info("分享任务已关闭")
        if self.config["LIKE_CD"] == 0 and self.config["SHARE_CD"] == 0:
            return
        try:
            if not failedMedals:
                failedMedals = self.medalsNeedDo
            if not self.config["ASYNC"]:
                log.info("同步点赞、分享任务开始....")
                for index, medal in enumerate(failedMedals):
                    tasks = []
                    tasks.append(
                        self.api.likeInteract(medal["room_info"]["room_id"])
                    ) if self.config["LIKE_CD"] else ...
                    tasks.append(
                        self.api.shareRoom(medal["room_info"]["room_id"])
                    ) if self.config["SHARE_CD"] else ...
                    await asyncio.gather(*tasks)
                    log.success(
                        f"{medal['anchor_info']['nick_name']} 点赞,分享成功 {index+1}/{len(self.medalsNeedDo)}",
                    )
                    await asyncio.sleep(
                        max(self.config["LIKE_CD"], self.config["SHARE_CD"])
                    )
            else:
                log.info("异步点赞、分享任务开始....")
                allTasks = []
                for medal in failedMedals:
                    allTasks.append(
                        self.api.likeInteract(medal["room_info"]["room_id"])
                    ) if self.config["LIKE_CD"] else ...
                    allTasks.append(
                        self.api.shareRoom(medal["room_info"]["room_id"])
                    ) if self.config["SHARE_CD"] else ...
                await asyncio.gather(*allTasks)
            await asyncio.sleep(10)
            await self.getMedals()  # 刷新勋章
            log.success("点赞、分享任务完成")
            finallyMedals = [
                medal
                for medal in self.medalsNeedDo
                if medal["medal"]["today_feed"] >= 200
            ]
            failedMedals = [
                medal
                for medal in self.medalsNeedDo
                if medal["medal"]["today_feed"] < 200
            ]
            msg = "20级以下牌子共 {} 个,完成任务 {} 个亲密度大于等于200".format(
                len(self.medalsNeedDo), len(finallyMedals)
            )
            log.info(msg)
            log.warning(
                "小于200或失败房间: {}... {}个".format(
                    " ".join(
                        [
                            medals["anchor_info"]["nick_name"]
                            for medals in failedMedals[:5]
                        ]
                    ),
                    len(failedMedals),
                ),
            )
            if self.retryTimes > self.maxRetryTimes:
                log.error("任务重试次数过多,停止任务")
                return
            if len(finallyMedals) / len(self.medalsNeedDo) <= 0.9:
                log.warning("成功率过低,重新执行任务")
                self.retryTimes += 1
                log.warning("重试次数: {}/{}".format(self.retryTimes, self.maxRetryTimes))
                await self.asynclikeandShare(failedMedals)
        except Exception:
            log.exception("点赞、分享任务异常")
            self.errmsg.append(f"【{self.name}】 点赞、分享任务异常,请检查日志")

    async def like_v3(self, failedMedals: Optional[list] = None):
        if failedMedals is None:
            failedMedals = []
        if self.config["LIKE_CD"] == 0:
            log.info("点赞任务已关闭")
            return
        try:
            if not failedMedals:
                failedMedals = self.medalsNeedDo
            if not self.config["ASYNC"]:
                log.info("同步点赞任务开始....")
                for index, medal in enumerate(failedMedals):
                    tasks = []
                    tasks.append(
                        self.api.likeInteractV3(
                            medal["room_info"]["room_id"],
                            medal["medal"]["target_id"],
                            self.mid,
                        )
                    ) if self.config["LIKE_CD"] else ...
                    await asyncio.gather(*tasks)
                    log.success(
                        f"{medal['anchor_info']['nick_name']} 点赞成功 {index+1}/{len(self.medalsNeedDo)}",
                    )
                    await asyncio.sleep(self.config["LIKE_CD"])
            else:
                log.info("异步点赞任务开始....")
                allTasks = []
                for medal in failedMedals:
                    allTasks.append(
                        self.api.likeInteractV3(
                            medal["room_info"]["room_id"],
                            medal["medal"]["target_id"],
                            self.mid,
                        )
                    ) if self.config["LIKE_CD"] else ...
                await asyncio.gather(*allTasks)
            await asyncio.sleep(10)
            log.success("点赞任务完成")
            finallyMedals = [
                medal
                for medal in self.medalsNeedDo
                if medal["medal"]["today_feed"] >= 100
            ]
            msg = "20级以下牌子共 {} 个,完成点赞任务 {} 个".format(
                len(self.medalsNeedDo), len(finallyMedals)
            )
            log.info(msg)
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
        log.info(
            "弹幕打卡任务开始....(预计 {} 秒完成)".format(
                len(self.medals) * self.config["DANMAKU_CD"]
            )
        )
        n = 0
        for medal in self.medals:
            try:
                (await self.api.wearMedal(medal["medal"]["medal_id"])) if self.config[
                    "WEARMEDAL"
                ] else ...
                danmaku = await self.api.sendDanmaku(medal["room_info"]["room_id"])
                n += 1
                log.success(
                    "{} 房间弹幕打卡成功: {} ({}/{})".format(
                        medal["anchor_info"]["nick_name"], danmaku, n, len(self.medals)
                    ),
                )
            except Exception as e:
                log.error("{} 房间弹幕打卡失败: {}".format(medal["anchor_info"]["nick_name"], e))
                self.errmsg.append(
                    f"【{self.name}】 {medal['anchor_info']['nick_name']} 房间弹幕打卡失败: {e!s}"
                )
            finally:
                await asyncio.sleep(self.config["DANMAKU_CD"])
        if hasattr(self, "initialMedal"):
            (await self.api.wearMedal(self.initialMedal["medal_id"])) if self.config[
                "WEARMEDAL"
            ] else ...
        log.success("弹幕打卡任务完成")
        self.message.append(f"【{self.name}】 弹幕打卡任务完成 {n}/{len(self.medals)}")
        if n >= 5:
            try:
                await self.api.getOneBattery()
                log.success("领取电池成功")
                self.message.append(f"【{self.name}】 领取电池成功")
            except Exception as e:
                log.error("领取电池失败: {}".format(e))
                self.errmsg.append(f"【{self.name}】 领取电池失败: {e!s}")

    async def init(self):
        if not await self.loginVerify():
            log.error("登录失败 可能是 access_key 过期 , 请重新获取")
            self.errmsg.append("登录失败 可能是 access_key 过期 , 请重新获取")
            await self.session.close()
        else:
            await self.doSign()
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
            if medal["medal"]["level"] >= 20:
                continue
            today_feed = medal["medal"]["today_feed"]
            nick_name = medal["anchor_info"]["nick_name"]
            if today_feed >= 1500:
                nameList1.append(nick_name)
            elif 1300 < today_feed <= 1400:
                nameList2.append(nick_name)
            elif 1200 < today_feed <= 1300:
                nameList3.append(nick_name)
            elif today_feed <= 1200:
                nameList4.append(nick_name)
        self.message.append(f"【{self.name}】 今日亲密度获取情况如下（20级以下）：")

        for l, n in zip(  # noqa: E741
            [nameList1, nameList2, nameList3, nameList4],
            ["【1500】", "【1300至1400】", "【1200至1300】", "【1200以下】"],
        ):
            if len(l) > 0:
                self.message.append(
                    f"{n}"
                    + " ".join(l[:5])
                    + f"{'等' if len(l) > 5 else ''}"
                    + f" {len(l)}个"
                )

        if hasattr(self, "initialMedal"):
            initialMedalInfo = await self.api.getMedalsInfoByUid(
                self.initialMedal["target_id"]
            )
            if initialMedalInfo["has_fans_medal"]:
                initialMedal = initialMedalInfo["my_fans_medal"]
                self.message.append(
                    f"【当前佩戴】「{initialMedal['medal_name']}」({initialMedal['target_name']}) {initialMedal['level']} 级 ",
                )
                if initialMedal["level"] < 20 and initialMedal["today_feed"] != 0:
                    need = initialMedal["next_intimacy"] - initialMedal["intimacy"]
                    need_days = need // 1500 + 1
                    end_date = datetime.now() + timedelta(days=need_days)
                    self.message.append(
                        f"今日已获取亲密度 {initialMedal['today_feed']} (B站结算有延迟，请耐心等待)",
                    )
                    self.message.append(
                        f"距离下一级还需 {need} 亲密度 预计需要 {need_days} 天 ({end_date.strftime('%Y-%m-%d')},以每日 1500 亲密度计算)",
                    )
        await self.session.close()
        return self.message + self.errmsg + ["---"]

    async def watchinglive(self):
        if not self.config["WATCHINGLIVE"]:
            log.info("每日观看不直播任务关闭")
            return
        HEART_MAX = self.config["WATCHINGLIVE"]
        log.info(f"每日{HEART_MAX}分钟任务开始")
        heartNum = 0
        while True:
            tasks = []
            for medal in self.medalsNeedDo:
                tasks.append(
                    self.api.heartbeat(
                        medal["room_info"]["room_id"], medal["medal"]["target_id"]
                    )
                )
            await asyncio.gather(*tasks)
            heartNum += 1
            log.info(
                f"{' '.join([medal['anchor_info']['nick_name'] for medal in self.medalsNeedDo[:5]])} 等共 {len(self.medalsNeedDo)} 个房间的第{heartNum}次心跳包已发送（{heartNum}/{HEART_MAX}）",
            )
            await asyncio.sleep(60)
            if heartNum >= HEART_MAX:
                break
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
                log.success(group["group_name"] + " 签到成功")
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
