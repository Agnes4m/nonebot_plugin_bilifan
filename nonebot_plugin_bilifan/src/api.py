import asyncio
import hashlib
import json
import random
import time
from hashlib import md5
from typing import Union
from urllib.parse import urlencode, urlparse

from aiohttp import ClientSession
from nonebot.log import logger

# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Crypto:
    APPKEY = "4409e2ce8ffd12b8"
    APPSECRET = "59b43e04ad6965f34319062b478f83dd"

    @staticmethod
    def md5(data: Union[str, bytes]) -> str:
        """generates md5 hex dump of `str` or `bytes`"""
        if isinstance(data, str):
            return md5(data.encode()).hexdigest()
        return md5(data).hexdigest()

    @staticmethod
    def sign(data: Union[str, dict]) -> str:
        """salted sign funtion for `dict`(converts to qs then parse) & `str`"""
        if isinstance(data, dict):
            _str = urlencode(data)
        elif not isinstance(data, str):
            raise TypeError
        return Crypto.md5(_str + Crypto.APPSECRET)  # type: ignore


class SingableDict(dict):
    @property
    def sorted(self):  # noqa: A003
        """returns a alphabetically sorted version of `self`"""
        return dict(sorted(self.items()))

    @property
    def signed(self):
        """returns our sorted self with calculated `sign` as a new key-value pair at the end"""
        _sorted = self.sorted
        return {**_sorted, "sign": Crypto.sign(_sorted)}


def retry(tries=3, interval=1):
    def decorate(func):
        async def wrapper(*args, **kwargs):
            count = 0
            func.isRetryable = False
            while True:
                try:
                    result = await func(*args, **kwargs)
                except Exception as E:
                    count += 1
                    if type(E) == BiliApiError:
                        if E.code == 1011040:
                            raise E  # noqa: TRY201
                        if E.code == 10030:
                            await asyncio.sleep(10)
                        elif E.code == -504:
                            pass
                        else:
                            raise E  # noqa: TRY201
                    if count > tries:
                        logger.error(f"API {urlparse(args[1]).path} 调用出现异常: {E!s}")
                        raise E  # noqa: TRY201
                    # log.error(f"API {urlparse(args[1]).path} 调用出现异常: {str(E)}，重试中，第{count}次重试")
                    await asyncio.sleep(interval)
                    func.isRetryable = True
                else:
                    if func.isRetryable:
                        pass
                        # log.success(f"重试成功")
                    return result

        return wrapper

    return decorate


def client_sign(data: dict):
    _str = json.dumps(data, separators=(",", ":"))
    for n in ["sha512", "sha3_512", "sha384", "sha3_384", "blake2b"]:
        _str = hashlib.new(n, _str.encode("utf-8")).hexdigest()
    return _str


def randomString(length: int = 16) -> str:
    return "".join(
        random.sample(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", length
        )
    )


class BiliApiError(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg

    def __str__(self):
        return self.msg


class BiliApi:
    headers = {  # noqa: RUF012
        "User-Agent": "Mozilla/5.0 BiliDroid/6.73.1 (bbcallen@gmail.com) os/android model/Mi 10 Pro mobi_app/android build/6731100 channel/xiaomi innerVer/6731110 osVer/12 network/2",
    }
    from .user import BiliUser

    def __init__(self, u: BiliUser, s: ClientSession):
        self.u = u
        self.session = s

    def __check_response(self, resp: dict) -> dict:
        if resp["code"] != 0 or ("mode_info" in resp["data"] and resp["message"] != ""):
            raise BiliApiError(resp["code"], resp["message"])
        return resp["data"]

    @retry()
    async def __get(self, *args, **kwargs):
        async with self.session.get(*args, **kwargs) as resp:
            return self.__check_response(await resp.json())

    @retry()
    async def __post(self, *args, **kwargs):
        async with self.session.post(*args, **kwargs) as resp:
            return self.__check_response(await resp.json())

    async def getFansMedalandRoomID(self) -> dict:  # type: ignore
        """
        获取用户粉丝勋章和直播间ID
        """
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/fansMedal/panel"
        params = {
            "access_key": self.u.access_key,
            "actionKey": "appkey",
            "appkey": Crypto.APPKEY,
            "ts": int(time.time()),
            "page": 1,
            "page_size": 50,
        }
        first_flag = True
        while True:
            data = await self.__get(
                url, params=SingableDict(params).signed, headers=self.headers
            )
            if first_flag and data["special_list"]:
                for item in data["special_list"]:
                    # 强制把正在佩戴的牌子加入任务列表
                    item["medal"]["today_feed"] = 0
                    yield item  # type: ignore
                self.u.wearedMedal = data["special_list"][0]  # type: ignore
                first_flag = False
            for item in data["list"]:
                yield item  # type: ignore
            if not data["list"]:
                break
            params["page"] += 1

    async def likeInteract(self, room_id: int):
        """
        点赞直播间
        """
        url = "https://api.live.bilibili.com/xlive/web-ucenter/v1/interact/likeInteract"
        data = {
            "access_key": self.u.access_key,
            "actionKey": "appkey",
            "appkey": Crypto.APPKEY,
            "click_time": 1,
            "roomid": room_id,
        }
        # for _ in range(3):
        await self.__post(
            url,
            data=SingableDict(data).signed,
            headers=self.headers.update(
                {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ),
        )
        # await asyncio.sleep(self.u.config['LIKE_CD'] if not self.u.config['ASYNC'] else 2)

    async def likeInteractV3(self, room_id: int, up_id: int, self_uid: int):
        """
        点赞直播间V3
        """
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/like_info_v3/like/likeReportV3"
        data = {
            "access_key": self.u.access_key,
            "actionKey": "appkey",
            "appkey": Crypto.APPKEY,
            "click_time": 1,
            "room_id": room_id,
            "anchor_id": up_id,
            "uid": self_uid,
        }
        # for _ in range(3):
        await self.__post(
            url,
            data=SingableDict(data).signed,
            headers=self.headers.update(
                {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ),
        )

    async def shareRoom(self, room_id: int):
        """
        分享直播间
        """
        url = "https://api.live.bilibili.com/xlive/app-room/v1/index/TrigerInteract"
        data = {
            "access_key": self.u.access_key,
            "actionKey": "appkey",
            "appkey": Crypto.APPKEY,
            "ts": int(time.time()),
            "interact_type": 3,
            "roomid": room_id,
        }
        # for _ in range(5):
        await self.__post(
            url,
            data=SingableDict(data).signed,
            headers=self.headers.update(
                {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ),
        )
        # await asyncio.sleep(self.u.config['SHARE_CD'] if not self.u.config['ASYNC'] else 5)

    async def sendDanmaku(self, room_id: int) -> str:
        """
        发送弹幕
        """
        url = "https://api.live.bilibili.com/xlive/app-room/v1/dM/sendmsg"
        danmakus = [
            "(⌒▽⌒).",
            "（￣▽￣）.",
            "(=・ω・=).",
            "(｀・ω・´).",
            "(〜￣△￣)〜.",
            "(･∀･).",
            "(°∀°)ﾉ.",
            "(￣3￣).",
            "╮(￣▽￣)╭.",
            "_(:3」∠)_.",
            "(^・ω・^ ).",
            "(●￣(ｴ)￣●).",
            "ε=ε=(ノ≧∇≦)ノ.",
            "⁄(⁄ ⁄•⁄ω⁄•⁄ ⁄)⁄.",
            "←◡←.",
        ]
        params = {
            "access_key": self.u.access_key,
            "actionKey": "appkey",
            "appkey": Crypto.APPKEY,
            "ts": int(time.time()),
        }
        data = {
            "cid": room_id,
            "msg": random.choice(danmakus),
            "rnd": int(time.time()),
            "color": "16777215",
            "fontsize": "25",
        }
        try:
            resp = await self.__post(
                url,
                params=SingableDict(params).signed,
                data=data,
                headers=self.headers.update(
                    {
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                ),
            )
        except BiliApiError as e:
            if e.code == 0:
                await asyncio.sleep(self.u.config["DANMAKU_CD"])
                params.update(
                    {
                        "ts": int(time.time()),
                    },
                )
                data.update(
                    {
                        "msg": "111",
                    },
                )
                resp = await self.__post(
                    url,
                    params=SingableDict(params).signed,
                    data=data,
                    headers=self.headers.update(
                        {
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                    ),
                )
                return json.loads(resp["mode_info"]["extra"])["content"]
            raise e
        return json.loads(resp["mode_info"]["extra"])["content"]

    async def loginVerift(self):
        """
        登录验证
        """
        url = "https://app.bilibili.com/x/v2/account/mine"
        params = {
            "access_key": self.u.access_key,
            "actionKey": "appkey",
            "appkey": Crypto.APPKEY,
            "ts": int(time.time()),
        }
        return await self.__get(
            url,
            params=SingableDict(params).signed,
            headers=self.headers,
        )

    async def doSign(self):
        """
        直播区签到
        """
        url = "https://api.live.bilibili.com/rc/v1/Sign/doSign"
        params = {
            "access_key": self.u.access_key,
            "actionKey": "appkey",
            "appkey": Crypto.APPKEY,
            "ts": int(time.time()),
        }
        return await self.__get(
            url,
            params=SingableDict(params).signed,
            headers=self.headers,
        )

    async def getUserInfo(self):
        """
        用户直播等级
        """
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/user/get_user_info"
        params = {
            "access_key": self.u.access_key,
            "actionKey": "appkey",
            "appkey": Crypto.APPKEY,
            "ts": int(time.time()),
        }
        return await self.__get(
            url,
            params=SingableDict(params).signed,
            headers=self.headers,
        )

    async def getMedalsInfoByUid(self, uid: int):
        """
        用户勋章信息
        """
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/fansMedal/fans_medal_info"
        params = {
            "access_key": self.u.access_key,
            "actionKey": "appkey",
            "appkey": Crypto.APPKEY,
            "ts": int(time.time()),
            "target_id": uid,
        }
        return await self.__get(
            url,
            params=SingableDict(params).signed,
            headers=self.headers,
        )

    # async def entryRoom(self, room_id: int, up_id: int):
    #     data = {
    #         "access_key": self.u.access_key,
    #         "actionKey": "appkey",
    #         "appkey": Crypto.APPKEY,
    #         "ts": int(time.time()),
    #         'platform': 'android',
    #         'uuid': self.u.uuids[0],
    #         'buvid': randomString(37).upper(),
    #         'seq_id': '1',
    #         'room_id': f'{room_id}',
    #         'parent_id': '6',
    #         'area_id': '283',
    #         'timestamp': f'{int(time.time())-60}',
    #         'secret_key': 'axoaadsffcazxksectbbb',
    #         'watch_time': '60',
    #         'up_id': f'{up_id}',
    #         'up_level': '40',
    #         'jump_from': '30000',
    #         'gu_id': randomString(43).lower(),
    #         'visit_id': randomString(32).lower(),
    #         'click_id': self.u.uuids[1],
    #         'heart_beat': '[]',
    #         'client_ts': f'{int(time.time())}'
    #     }
    #     url = "http://live-trace.bilibili.com/xlive/data-interface/v1/heartbeat/mobileEntry"
    #     return await self.__post(url, data=SingableDict(data).signed, headers=self.headers.update({
    #         "Content-Type": "application/x-www-form-urlencoded",
    #     }))

    async def heartbeat(self, room_id: int, up_id: int):
        url = "https://live-trace.bilibili.com/xlive/data-interface/v1/heartbeat/mobileHeartBeat"
        data = {
            "platform": "android",
            "uuid": self.u.uuids[0],
            "buvid": randomString(37).upper(),
            "seq_id": "1",
            "room_id": f"{room_id}",
            "parent_id": "6",
            "area_id": "283",
            "timestamp": f"{int(time.time())-60}",
            "secret_key": "axoaadsffcazxksectbbb",
            "watch_time": "60",
            "up_id": f"{up_id}",
            "up_level": "40",
            "jump_from": "30000",
            "gu_id": randomString(43).lower(),
            "play_type": "0",
            "play_url": "",
            "s_time": "0",
            "data_behavior_id": "",
            "data_source_id": "",
            "up_session": f"l:one:live:record:{room_id}:{int(time.time())-88888}",
            "visit_id": randomString(32).lower(),
            "watch_status": "%7B%22pk_id%22%3A0%2C%22screen_status%22%3A1%7D",
            "click_id": self.u.uuids[1],
            "session_id": "",
            "player_type": "0",
            "client_ts": f"{int(time.time())}",
        }
        data.update(
            {
                "client_sign": client_sign(data),
                "access_key": self.u.access_key,
                "actionKey": "appkey",
                "appkey": Crypto.APPKEY,
                "ts": int(time.time()),
            }  # type: ignore
        )  # type: ignore
        return await self.__post(
            url,
            data=SingableDict(data).signed,
            headers=self.headers.update(
                {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ),
        )

    async def wearMedal(self, medal_id: int):
        """
        佩戴粉丝牌
        """
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/fansMedal/wear"
        data = {
            "access_key": self.u.access_key,
            "actionKey": "appkey",
            "appkey": Crypto.APPKEY,
            "ts": int(time.time()),
            "medal_id": medal_id,
            "platform": "android",
            "type": "1",
            "version": "0",
        }
        return await self.__post(
            url,
            data=SingableDict(data).signed,
            headers=self.headers.update(
                {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ),
        )

    async def getGroups(self):
        url = "https://api.live.bilibili.com/link_group/v1/member/my_groups"
        params = {
            "access_key": self.u.access_key,
            "actionKey": "appkey",
            "appkey": Crypto.APPKEY,
            "ts": int(time.time()),
        }
        list = (  # noqa: A001
            await self.__get(
                url, params=SingableDict(params).signed, headers=self.headers
            )
        )["list"]
        for group in list:
            yield group

    async def signInGroups(self, group_id: int, owner_id: int):
        url = "https://api.vc.bilibili.com/link_setting/v1/link_setting/sign_in"
        params = {
            "access_key": self.u.access_key,
            "actionKey": "appkey",
            "appkey": Crypto.APPKEY,
            "ts": int(time.time()),
            "group_id": group_id,
            "owner_id": owner_id,
        }
        return await self.__get(
            url,
            params=SingableDict(params).signed,
            headers=self.headers,
        )

    async def getOneBattery(self):
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/userTask/UserTaskReceiveRewards"
        data = {
            "access_key": self.u.access_key,
            "actionKey": "appkey",
            "appkey": Crypto.APPKEY,
            "ts": int(time.time()),
        }
        return await self.__post(
            url,
            data=SingableDict(data).signed,
            headers=self.headers,
        )
