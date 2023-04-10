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

def login():
    global access_key, csrf, Cookies
    filename = "login_info.json"
    try:
        with open(filename, "r") as f:
            data = f.read()
            if len(data) == 0:
                print("未登录,请扫码登录")
                loginBili()
            else:
                access_key = json.loads(data)["data"]["access_token"]
                for c in json.loads(data)["data"]["cookie_info"]["cookies"]:
                    Cookies.append({
                        "name": c["name"],
                        "value": c["value"]
                    })
                    if c["name"] == "bili_jct":
                        csrf = c["value"]
                logged_in, name = is_login()
                if logged_in:
                    print("登录成功：", name)
                else:
                    print("登录失败，请重新扫码登录")
                    loginBili()
    except FileNotFoundError:
        print("未登录,请扫码登录")
        loginBili()


def is_login():
    global cookies
    api = "https://api.bilibili.com/x/web-interface/nav"
    req = urllib.request.Request(api)
    for c in cookies:
        req.add_header("Cookie", f"{c['name']}={c['value']}")
    with urllib.request.urlopen(req) as response:
        body = response.read().decode()
        data = json.loads(body)
        return data["code"] == 0, data["data"]["uname"]

def signature(data):
    secret_key = "560c52ccd288fed045859ed18bffd973"
    keys = sorted(data.keys())
    sig_str = ""
    for key in keys:
        sig_str += f"{key}={data[key]}"
    sig_str += secret_key
    m = hashlib.md5()
    m.update(sig_str.encode("utf-8"))
    sign = m.hexdigest()
    data["sign"] = sign


def map_to_string(data):
    string = ""
    keys = sorted(data.keys())
    for key in keys:
        string += f"{key}={data[key]}&"
    return string[:-1]



def is_login():
    api = 'https://api.bilibili.com/x/web-interface/nav'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    session = requests.Session()
    for c in Cookies:
        session.cookies.set(c['name'], c['value'])
    resp = session.get(api, headers=headers)
    data = resp.json()
    return data['code'] == 0, data['data']['uname']

def get_tv_qrcode_url_and_auth_code():
    api = 'http://passport.bilibili.com/x/passport-tv-login/qrcode/auth_code'
    data = {
        "local_id": "0",
        "ts": str(int(time.time())),
    }
    signature(data)
    resp = requests.post(api, data=map_to_string(data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    resp_data = resp.json()
    code = resp_data['code']
    if code == 0:
        qrcode_url = resp_data['data']['url']
        auth_code = resp_data['data']['auth_code']
        return qrcode_url, auth_code
    else:
        raise Exception('get_tv_qrcode_url_and_auth_code error')

def signature(params):
    keys = list(params.keys())
    params["appkey"] = appkey
    keys.append("appkey")
    keys.sort()
    query = ""
    for k in keys:
        query += k + "=" + urllib.parse.quote(params[k]) + "&"
    query += "appseccret"
    hash = hashlib.md5()
    hash.update(query.encode("utf-8"))
    params["sign"] = hash.hexdigest()

def map_to_string(params):
    query = ""
    for k, v in params.items():
        query += k + "=" + v + "&"
    return query[:-1]

def verify_login(auth_code):
    api = "http://passport.bilibili.com/x/passport-tv-login/qrcode/poll"
    data = {
        "auth_code": auth_code,
        "local_id": "0",
        "ts": str(int(time.time())),
    }
    signature(data)
    data_string = map_to_string(data)
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

def signature(params: dict):
    keys = list(params.keys())
    params["appkey"] = appkey
    keys.append("appkey")
    keys.sort()
    query = "&".join([k + "=" + urlparse.quote(params[k]) for k in keys])
    query += appsec
    hash = hashlib.md5(query.encode("utf-8"))
    params["sign"] = hash.hexdigest()

def map_to_string(params: dict) -> str:
    query = "&".join([k + "=" + v for k, v in params.items()])
    return query

def draw_QR(login_url):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(login_url)
    qr.make(fit=True)
    img:Image = qr.make_image(fill_color="black", back_color="white")
    return img
    # img.save("qrcode.png")


def loginBili():
    print("请最大化窗口，以确保二维码完整显示，回车继续")
    
    login_url, auth_code = get_tv_qrcode_url_and_auth_code()
    qrcode_terminal.draw(login_url)
    print("或将此链接复制到手机B站打开:", login_url)
    while True:
        if verify_login(auth_code):
            print("登录成功！")
            break
        else:
            time.sleep(3)
            print("等待扫码登录中...")
            
def main():
    loginBili()
    input()

if __name__ == "__main__":
    main()
