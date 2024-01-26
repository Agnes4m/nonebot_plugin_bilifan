import asyncio
import hashlib
import shutil
import time
import urllib.parse as urlparse
from io import BytesIO
from pathlib import Path

import aiohttp

# import qrcode_terminal
import qrcode
import yaml
from nonebot.log import logger

# Cookies = cookiejar.CookieJar()
# session = requests.Session()
# session.cookies = Cookies

csrf = ""
access_key = ""
base_path = Path().joinpath("data/bilifan")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
}


async def is_login(session, cookies):
    api = "https://api.bilibili.com/x/web-interface/nav"

    async with session.get(api, headers=headers, cookies=cookies) as resp:
        data = await resp.json()
        return data["code"] == 0, data["data"]["uname"]


async def get_tv_qrcode_url_and_auth_code():
    api = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
    data = {
        "local_id": "0",
        "ts": str(int(time.time())),
    }
    await signature(data)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            api,
            data=await map_to_string(data),
            headers=headers,
            # headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as resp:
            resp_data = await resp.json()
            print(resp_data)
            code = resp_data["code"]
            if code == 0:
                login_url = resp_data["data"]["url"]
                login_key = resp_data["data"]["qrcode_key"]
                return login_url, login_key
            raise Exception("get_tv_qrcode_url_and_auth_code error")


async def verify_login(login_key: str, data_path: Path):
    api = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
    # data = {
    #     "auth_code": api,
    #     "local_id": "0",
    #     "ts": str(int(time.time())),
    # }
    api += "?" + "qrcode_key=" + login_key
    # await signature(data)
    # data_string = await map_to_string(data)
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.get(api, headers=headers) as resp:
                if resp.status != 200:
                    raise Exception("Failed to connect to server")
                response_dict = await resp.json()
                print(response_dict)
                url = response_dict["data"]["url"]
                access_key = response_dict["data"]["refresh_token"]
                print(access_key)
                cookie = {}
                filename = "login_info.txt"
                cookie_content = ""
                try:
                    kv_arr = []
                    for _, v in resp.headers["Set-Cookie"]:
                        kv = v.split(";")[0].strip()
                        kv_arr = kv.split("=")
                    print(f"kr代码:{kv_arr}")
                    cookie[kv_arr[0]] = kv_arr[1]
                    filename: str = cookie["DedeUserID"] + "_cookie.txt"
                    cookie_content = f"DedeUserID={cookie['DedeUserID']};DedeUserID__ckMd5={cookie['DedeUserID__ckMd5']};Expires={cookie['Expires']};SESSDATA={cookie['SESSDATA']};bili_jct={cookie['bili_jct']};"
                    print(f"ck代码{cookie_content}")

                except Exception:
                    # access_key = ""
                    await asyncio.sleep(3)

            if url != "":
                logger.success("登录成功")
                data_path.mkdir(parents=True, exist_ok=True)
                print(f"access_key代码{access_key}")
                with (data_path / filename).open(mode="w", encoding="utf-8") as f:
                    f.write(access_key)
                if not Path(data_path / "users.yaml").is_file():
                    logger.info("初始化配置文件")
                    shutil.copy2(
                        Path().joinpath("data/bilifan/users.yaml"),
                        data_path / "users.yaml",
                    )
                with Path(data_path / "users.yaml").open("r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                config["USERS"][0]["access_key"] = access_key
                with Path(data_path / "users.yaml").open("w", encoding="utf-8") as f:
                    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                return "access_key已保存"
            await asyncio.sleep(3)


appkey = "4409e2ce8ffd12b8"
appsec = "59b43e04ad6965f34319062b478f83dd"


async def signature(params: dict):
    keys = list(params.keys())
    params["appkey"] = appkey
    keys.append("appkey")
    keys.sort()
    query = "&".join([k + "=" + urlparse.quote(params[k]) for k in keys])
    query += appsec
    hash_ = hashlib.md5(query.encode("utf-8"))
    params["sign"] = hash_.hexdigest()


async def map_to_string(params: dict) -> str:
    return "&".join([k + "=" + v for k, v in params.items()])


async def draw_QR(login_url: str):  # noqa: N802
    "绘制二维码"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)  # type: ignore
    qr.add_data(login_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
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
