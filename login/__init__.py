import hashlib
import urllib.parse as urlparse
import time
import urllib
import requests
import json
from http import cookiejar
import requests
import time
import hashlib
import urllib.parse as urlparse

import qrcode_terminal
import qrcode
from PIL import Image

Cookies = cookiejar.CookieJar()
session = requests.Session()
session.cookies = Cookies

csrf = ""
access_key = ""


# async def is_login():
    # global cookies
    # api = "https://api.bilibili.com/x/web-interface/nav"
    # req = urllib.request.Request(api)
    # for c in cookies:
        # req.add_header("Cookie", f"{c['name']}={c['value']}")
    # with urllib.request.urlopen(req) as response:
        # body = response.read().decode()
        # data = json.loads(body)
        # return data["code"] == 0, data["data"]["uname"]




async def map_to_string(data):
    string = ""
    keys = sorted(data.keys())
    for key in keys:
        string += f"{key}={data[key]}&"
    return string[:-1]



async def is_login():
    api = 'https://api.bilibili.com/x/web-interface/nav'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    session = requests.Session()
    for c in Cookies:
        session.cookies.set(c['name'], c['value'])
    resp = session.get(api, headers=headers)
    data = resp.json()
    return data['code'] == 0, data['data']['uname']

async def get_tv_qrcode_url_and_auth_code():
    api = 'http://passport.bilibili.com/x/passport-tv-login/qrcode/auth_code'
    data = {
        "local_id": "0",
        "ts": str(int(time.time())),
    }
    await signature(data)
    resp = requests.post(api, data= await map_to_string(data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    resp_data = resp.json()
    code = resp_data['code']
    if code == 0:
        qrcode_url = resp_data['data']['url']
        auth_code = resp_data['data']['auth_code']
        return qrcode_url, auth_code
    else:
        raise Exception('get_tv_qrcode_url_and_auth_code error')


# async def map_to_string(params):
    # query = ""
    # for k, v in params.items():
        # query += k + "=" + v + "&"
    # return query[:-1]

async def verify_login(auth_code):
    api = "http://passport.bilibili.com/x/passport-tv-login/qrcode/poll"
    data = {
        "auth_code": auth_code,
        "local_id": "0",
        "ts": str(int(time.time())),
    }
    await signature(data)
    data_string = await map_to_string(data)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    while True:
        resp = requests.post(api, headers=headers, data=data_string)
        if resp.status_code != 200:
            raise Exception("Failed to connect to server")
        response_dict = json.loads(resp.text)
        code = response_dict["code"]
        try:
            access_key = response_dict["data"]["access_token"]
        except:
            time.sleep(3)
            
        if code == 0:
            print("登录成功")
            print("access_key:", access_key)
            filename = "login_info.txt"
            with open(filename, "w") as f:
                f.write(access_key)
            print("access_key已保存在", filename)
            break
        else:
            time.sleep(3)

appkey = "4409e2ce8ffd12b8"
appsec = "59b43e04ad6965f34319062b478f83dd"

async def signature(params: dict):
    keys = list(params.keys())
    params["appkey"] = appkey
    keys.append("appkey")
    keys.sort()
    query = "&".join([k + "=" + urlparse.quote(params[k]) for k in keys])
    query += appsec
    hash = hashlib.md5(query.encode("utf-8"))
    params["sign"] = hash.hexdigest()

async def map_to_string(params: dict) -> str:
    query = "&".join([k + "=" + v for k, v in params.items()])
    return query

async def draw_QR(login_url):
    "绘制二维码"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(login_url)
    qr.make(fit=True)
    img:Image = qr.make_image(fill_color="black", back_color="white")
    return img
    # img.save("qrcode.png")


async def loginBili():
    
    login_url, auth_code = await get_tv_qrcode_url_and_auth_code()
    qrcode_terminal.draw(login_url)
    print("或将此链接复制到手机B站打开:", login_url)
    while True:
        if await verify_login(auth_code):
            print("登录成功！")
            break
        else:
            time.sleep(3)
            print("等待扫码登录中...")
            
async def main():
    loginBili()
    input()

if __name__ == "__main__":
    main()
