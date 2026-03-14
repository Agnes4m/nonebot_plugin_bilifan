import asyncio
import hashlib
import shutil
import time
import urllib.parse as urlparse
from io import BytesIO
from pathlib import Path

import aiohttp
import anyio
import qrcode
import yaml
from nonebot.log import logger

csrf = ""
access_key = ""
base_path = Path().joinpath("data/bilifan")


async def is_login(session, cookies):
    api = "https://api.bilibili.com/x/web-interface/nav"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 Edg/97.0.1072.69",
    }
    async with session.get(api, headers=headers, cookies=cookies) as resp:
        data = await resp.json()
        return data["code"] == 0, data["data"]["uname"]


async def get_tv_qrcode_url_and_auth_code():
    api = "https://passport.bilibili.com/x/passport-tv-login/qrcode/auth_code"
    data = {
        "local_id": "0",
        "ts": str(int(time.time())),
    }
    await signature(data)
    async with aiohttp.ClientSession() as session:
        async with session.post(
            api,
            data=await map_to_string(data),
            cookies={},
            headers={
                "Host": "passport.bilibili.com",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 Edg/97.0.1072.69",
            },
        ) as resp:
            if resp.status != 200:
                raise Exception("Failed to connect to server")
            resp_data = await resp.json()
            code = resp_data["code"]
            if code == 0:
                login_url = resp_data["data"]["url"]
                login_key = resp_data["data"]["auth_code"]
                return login_url, login_key
            raise Exception("get_tv_qrcode_url_and_auth_code error")


async def get_user_info(access_key: str):
    """获取B站用户信息"""
    api = "https://api.bilibili.com/x/space/myinfo"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 Edg/97.0.1072.69",
    }
    params = {
        "access_key": access_key,
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(api, headers=headers, params=params) as resp:
            if resp.status != 200:
                raise Exception("Failed to get user info")
            data = await resp.json()
            if data["code"] == 0:
                return data["data"]["mid"], data["data"]["name"]
            raise Exception(f"获取用户信息失败: {data.get('message', 'Unknown error')}")


async def refresh_access_key(refresh_token: str, access_key: str):
    """刷新access_key"""
    api = "https://passport.bilibili.com/x/passport-tv-login/token/refresh"
    data = {
        "access_token": access_key,
        "refresh_token": refresh_token,
        "ts": str(int(time.time())),
    }
    await signature(data)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            api,
            data=await map_to_string(data),
            headers={
                "Host": "passport.bilibili.com",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 Edg/97.0.1072.69",
            },
        ) as resp:
            if resp.status != 200:
                raise Exception("Failed to refresh token")
            response_dict = await resp.json()
            if response_dict["code"] == 0:
                new_access_key = response_dict["data"]["access_token"]
                new_refresh_token = response_dict["data"]["refresh_token"]
                logger.success("access_key刷新成功")
                return new_access_key, new_refresh_token
            else:
                raise Exception(
                    f"刷新失败: {response_dict.get('message', 'Unknown error')}"
                )


async def verify_login(login_key: str, data_path: Path):
    api = "https://passport.bilibili.com/x/passport-tv-login/qrcode/poll"
    data = {
        "auth_code": login_key,
        "local_id": "0",
        "ts": str(int(time.time())),
    }
    await signature(data)
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api,
                data=await map_to_string(data),
                cookies={},
                headers={
                    "Host": "passport.bilibili.com",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 Edg/97.0.1072.69",
                },
            ) as resp:
                if resp.status != 200:
                    raise Exception("Failed to connect to server")
                response_dict = await resp.json()
                code = response_dict["code"]
                try:
                    access_key = response_dict["data"]["access_token"]
                    refresh_token = response_dict["data"].get("refresh_token", "")
                except Exception:
                    access_key = ""
                    refresh_token = ""
                    await asyncio.sleep(3)

            if code == 0:
                logger.success("登录成功")

                # 获取B站用户信息
                try:
                    bili_uid, bili_name = await get_user_info(access_key)
                    logger.info(f"获取到B站用户信息: UID={bili_uid}, 昵称={bili_name}")
                except Exception as e:
                    logger.error(f"获取用户信息失败: {e}")
                    return False

                filename = "login_info.txt"
                data_path.mkdir(parents=True, exist_ok=True)
                with (data_path / filename).open(mode="w", encoding="utf-8") as f:
                    f.write(access_key)

                # 保存refresh_token
                if refresh_token:
                    with (data_path / "refresh_token.txt").open(
                        mode="w", encoding="utf-8"
                    ) as f:
                        f.write(refresh_token)
                    logger.info("refresh_token已保存")

                if not Path(data_path / "users.yaml").is_file():
                    logger.info("初始化配置文件")
                    shutil.copy2(
                        Path().joinpath("data/bilifan/users.yaml"),
                        data_path / "users.yaml",
                    )

                config = yaml.safe_load(
                    await anyio.Path(data_path / "users.yaml").read_text("u8"),
                )

                # 查找是否已存在该B站用户
                existing_index = -1
                for i, user in enumerate(config["USERS"]):
                    if user.get("bili_uid") == bili_uid:
                        existing_index = i
                        logger.info(
                            f"检测到B站用户 {bili_name}(UID:{bili_uid}) 已存在，将更新access_key"
                        )
                        break

                if existing_index >= 0:
                    # 顶替旧的access_key并清除过期标记
                    config["USERS"][existing_index]["access_key"] = access_key
                    config["USERS"][existing_index]["bili_name"] = bili_name
                    config["USERS"][existing_index]["is_expired"] = False
                    if refresh_token:
                        config["USERS"][existing_index]["refresh_token"] = refresh_token
                    result_msg = (
                        f"已更新B站用户 {bili_name}(UID:{bili_uid}) 的access_key"
                    )
                else:
                    # 新增用户
                    new_user = {
                        "access_key": access_key,
                        "bili_uid": bili_uid,
                        "bili_name": bili_name,
                        "white_uid": 0,
                        "banned_uid": 0,
                        "is_expired": False,
                    }
                    if refresh_token:
                        new_user["refresh_token"] = refresh_token
                    config["USERS"].append(new_user)
                    result_msg = f"已添加新的B站用户 {bili_name}(UID:{bili_uid})"
                    logger.info(result_msg)

                yaml_string = yaml.dump(
                    config,
                    allow_unicode=True,
                    default_flow_style=False,
                )
                await anyio.Path(data_path / "users.yaml").write_text(yaml_string, "u8")

                return result_msg
            await asyncio.sleep(3)


appkey = "4409e2ce8ffd12b8"
appsec = "59b43e04ad6965f34319062b478f83dd"


async def signature(params: dict):  # noqa: RUF029
    keys = list(params.keys())
    params["appkey"] = appkey
    keys.append("appkey")
    keys.sort()
    query = "&".join([k + "=" + urlparse.quote(params[k]) for k in keys])
    query += appsec
    hash_ = hashlib.md5(query.encode("utf-8"))
    params["sign"] = hash_.hexdigest()


async def map_to_string(params: dict) -> str:  # noqa: RUF029
    return "&".join([k + "=" + v for k, v in params.items()])


async def draw_QR(login_url: str):  # noqa: N802, RUF029
    "绘制二维码"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)  # type: ignore
    qr.add_data(login_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")  # pyright: ignore[reportCallIssue]
    return buffered.getvalue()
    # img.save("qrcode.png")


# async def loginBili():


#     login_url, auth_code = await get_tv_qrcode_url_and_auth_code()
#     qrcode_terminal.draw(login_url)
#     print("或将此链接复制到手机B站打开:", login_url)
#     while True:
#         if await verify_login(auth_code):
#             print("登录成功！")
#             break
#         else:
#             time.sleep(3)
#             print("等待扫码登录中...")


# async def main():
#     loginBili()
#     input()

# if __name__ == "__main__":
#     main()
