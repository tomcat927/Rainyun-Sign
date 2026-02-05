##搬运来源出处！！！ 妖火-吃橘子的猫
##搬运来源出处！！！ 妖火-吃橘子的猫
##搬运来源出处！！！ 妖火-吃橘子的猫
##搬运来源出处！！！ 妖火-吃橘子的猫
##搬运来源出处！！！ 妖火-吃橘子的猫
##搬运来源出处！！！ 妖火-吃橘子的猫
##搬运来源出处！！！ 妖火-吃橘子的猫
##搬运来源出处！！！ 妖火-吃橘子的猫
##搬运来源出处！！！ 妖火-吃橘子的猫
# 品赞的API 有效期1分钟  socks5 txt返回格式
import socket
import socks
import requests
import json
import os
from typing import Tuple, Optional
from dataclasses import dataclass


try:
    from notify import send
except ImportError:
    print("通知服务加载失败，请检查notify.py是否存在")
    exit(1)


@dataclass
class UserInfo:
    name: str
    email: str
    points: int
    last_ip: str
    last_login_area: str


class RainyunAPI:
    BASE_URL = "https://api.v2.rainyun.com"
    VERIFY_URL = "http://119.96.239.11:8888/api/getcode"
    PROXY_API_URL = ""  # 品赞的API 有效期1分钟  socks5 txt返回格式
    
    def __init__(self):
        self.session = requests.Session()
        self.csrf_token = None
        self.proxy = None  # 存储代理信息
        
        # 获取代理并设置
        self.set_proxy()

    def set_proxy(self):
        # 调用品赞的API获取代理
        try:
            response = requests.get(self.PROXY_API_URL)
            response.raise_for_status()
            proxy_address = response.text.strip()  # 获取代理地址和端口
            
            if proxy_address:
                proxy_parts = proxy_address.split(':')
                if len(proxy_parts) == 2:
                    ip, port = proxy_parts
                    socks.set_default_proxy(socks.SOCKS5, ip, int(port))  # 设置SOCKS5代理
                    socket.socket = socks.socksocket  # 替换默认的socket
                    self.proxy = (ip, int(port))
                    print(f"代理设置成功: {self.proxy}")
                else:
                    print("代理格式错误")
            else:
                print("未能获取有效的代理")
        except Exception as e:
            print(f"获取代理失败: {str(e)}")

    def get_slide_verify(self) -> Tuple[str, str]:
        verify_token = os.getenv("VERIFY_TOKEN")
        if not verify_token:
            print("错误：未设置VERIFY_TOKEN环境变量")
            return "", ""
            
        headers = {"Content-Type": "application/json"}
        data = {
            "timeout": "60",
            "type": "tencent-turing",
            "appid": "2039519451",
            "token": verify_token,
            "developeraccount": "qqaoxin",
            "referer": "https://dl.reg.163.com/"
        }
        
        try:
            response = self.session.post(self.VERIFY_URL, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == 200 and result.get("success"):
                verify_data = json.loads(result["data"]["code"])
                return verify_data.get("ticket", ""), verify_data.get("randstr", "")
            
            print(f"验证码服务返回错误: {result.get('msg')}")
            return "", ""
            
        except Exception as e:
            print(f"验证码请求异常: {str(e)}")
            return "", ""

    def login(self, username: str, password: str) -> bool:
        login_data = json.dumps({
            "field": username,
            "password": password
        })
        headers = {"Content-Type": "application/json"}
        
        try:
            response = self.session.post(
                f"{self.BASE_URL}/user/login",
                headers=headers,
                data=login_data,
                timeout=30
            )
            response.raise_for_status()
            
            self.csrf_token = response.cookies.get_dict().get('X-CSRF-Token')
            return bool(self.csrf_token)
            
        except Exception as e:
            print(f"登录失败: {str(e)}")
            return False

    def get_user_info(self) -> Optional[UserInfo]:
        if not self.csrf_token:
            return None
            
        headers = {
            "Content-Type": "application/json",
            'x-csrf-token': self.csrf_token
        }
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}/user/?no_cache=false",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()['data']
            return UserInfo(
                name=data['Name'],
                email=data['Email'],
                points=data['Points'],
                last_ip=data['LastIP'],
                last_login_area=data['LastLoginArea']
            )
            
        except Exception as e:
            print(f"获取用户信息失败: {str(e)}")
            return None

    def sign_in(self, ticket: str, randstr: str) -> Tuple[bool, str]:
        if not self.csrf_token:
            return False, "签到失败：未获取到csrf_token"
            
        signin_data = json.dumps({
            "task_name": "每日签到",
            "verifyCode": "",
            "vticket": ticket,
            "vrandstr": randstr
        })
        headers = {
            'x-csrf-token': self.csrf_token
        }
        
        try:
            response = self.session.post(
                f"{self.BASE_URL}/user/reward/tasks",
                headers=headers,
                data=signin_data,
                timeout=30
            )
            
            try:
                result = response.json()
            except:
                return False, f"签到失败：HTTP {response.status_code}, 响应内容: {response.text}"
            
            if result.get("code") == 200:
                return True, "签到成功"
            else:
                return False, f"签到失败：{result.get('message', '未知错误')} (code: {result.get('code')})"
            
        except Exception as e:
            return False, f"签到异常：{str(e)}"


def process_account(credentials: str) -> str:
    try:
        username, password = credentials.split('&')
    except ValueError:
        return "\n账户格式错误，请使用&分隔用户名和密码"

    api = RainyunAPI()
    
    if not api.login(username, password):
        return f'\n【用户名】{username}\n【签到状态】登录失败'

    ticket, randstr = api.get_slide_verify()
    if not ticket or not randstr:
        return f'\n【用户名】{username}\n【签到状态】滑块验证失败'

    user_info = api.get_user_info()
    if not user_info:
        return f'\n【用户名】{username}\n【签到状态】获取用户信息失败'

    success, sign_message = api.sign_in(ticket, randstr)
    
    return (f'\n【用户名】{username}\n'
            f'【电子邮件】{user_info.email}\n'
            f'【签到状态】{sign_message}\n'
            f'【剩余积分】{user_info.points}\n'
            f'【最后登录ip】{user_info.last_ip}\n'
            f'【最后登录地址】{user_info.last_login_area}')


def main():
    credentials = os.getenv("yyqd")
    if not credentials:
        print("错误：未设置yyqd环境变量")
        return
        
    verify_token = os.getenv("VERIFY_TOKEN")
    if not verify_token:
        print("错误：未设置VERIFY_TOKEN环境变量")
        return

    results = []
    for account in credentials.split('#'):
        result = process_account(account)
        results.append(result)

    combined_message = "-"*45 + "\n".join(results)
    print("###雨云签到###\n\n", combined_message)
    
    send("雨云签到", combined_message)


if __name__ == '__main__':
    main()
