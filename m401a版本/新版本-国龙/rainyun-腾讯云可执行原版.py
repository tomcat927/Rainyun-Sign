import logging
import os
import random
import re
import time
import hashlib
import hmac
import base64
import urllib.parse
import time as time_module

import cv2
import ddddocr
import requests
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# === 钉钉机器人配置 ===
DINGTALK_TOKEN = "f7ed30834e11b7b52b06363ca15f8bce1879c8bcea3c89f58eb9124c2fcd7fd8"
DINGTALK_SECRET = "SEC71d9ff55c0c57b1e71e2c8be08a3b054847080c4a8ebcc3e885ec12c28279abf"

# === 多账号配置 ===
ACCOUNTS = [
    {"user": "maya10", "pwd": "qwer@345"},
    # 可在此添加更多账号，例如：
    {"user": "派太星星", "pwd": "2002815qaz"},
    # {"user": "user3", "pwd": "pass3"},
]

# 全局配置
DEBUG = True
LINUX = True
TIMEOUT = 300
MAX_DELAY = 90
VER = "2.1c-multi"


def send_dingtalk_message(msg: str):
    """发送带加签的钉钉机器人消息"""
    try:
        timestamp = str(round(time_module.time() * 1000))
        secret_enc = DINGTALK_SECRET.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, DINGTALK_SECRET)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        webhook_url = f"https://oapi.dingtalk.com/robot/send?access_token={DINGTALK_TOKEN}&timestamp={timestamp}&sign={sign}"
        headers = {'Content-Type': 'application/json'}
        data = {"msgtype": "text", "text": {"content": msg}}
        response = requests.post(webhook_url, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            logger.info("钉钉消息发送成功")
        else:
            logger.error(f"钉钉消息发送失败: {response.text}")
    except Exception as e:
        logger.error(f"发送钉钉通知异常: {e}")


def init_selenium() -> WebDriver:
    ops = Options()
    ops.add_argument("--no-sandbox")
    if DEBUG:
        ops.add_experimental_option("detach", True)
    if LINUX:
        ops.add_argument("--headless")
        ops.add_argument("--disable-gpu")
        ops.add_argument("--disable-dev-shm-usage")
        ops.add_argument("--window-size=1920,1080")
        ops.binary_location = "/usr/local/bin/chrome-headless-shell"
        service1 = Service("/usr/local/bin/chromedriver")
        return webdriver.Chrome(service=service1, options=ops)
    return webdriver.Chrome(service=Service("chromedriver.exe"), options=ops)


def download_image(url, filename):
    os.makedirs("temp", exist_ok=True)
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        path = os.path.join("temp", filename)
        with open(path, "wb") as f:
            f.write(response.content)
        return True
    else:
        logger.error("下载图片失败！")
        return False


def get_url_from_style(style):
    return re.search(r'url\(["\']?(.*?)["\']?\)', style).group(1)


def get_width_from_style(style):
    return re.search(r'width:\s*([\d.]+)px', style).group(1)


def get_height_from_style(style):
    return re.search(r'height:\s*([\d.]+)px', style).group(1)


def check_captcha() -> bool:
    raw = cv2.imread("temp/sprite.jpg")
    for i in range(3):
        w = raw.shape[1]
        temp = raw[:, w // 3 * i: w // 3 * (i + 1)]
        cv2.imwrite(f"temp/sprite_{i + 1}.jpg", temp)
        with open(f"temp/sprite_{i + 1}.jpg", mode="rb") as f:
            temp_rb = f.read()
        if ocr.classification(temp_rb) in ["0", "1"]:
            return False
    return True


def check_answer(d: dict) -> bool:
    flipped = {}
    for key in d.keys():
        flipped[d[key]] = key
    return len(d.values()) == len(flipped.keys())


def compute_similarity(img1_path, img2_path):
    img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)
    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(img1, None)
    kp2, des2 = sift.detectAndCompute(img2, None)
    if des1 is None or des2 is None:
        return 0.0, 0
    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)
    good = [m for m_n in matches if len(m_n) == 2 for m, n in [m_n] if m.distance < 0.8 * n.distance]
    if len(good) == 0:
        return 0.0, 0
    similarity = len(good) / len(matches)
    return similarity, len(good)


def download_captcha_img(wait):
    if os.path.exists("temp"):
        for filename in os.listdir("temp"):
            file_path = os.path.join("temp", filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
    slideBg = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="slideBg"]')))
    img1_style = slideBg.get_attribute("style")
    img1_url = get_url_from_style(img1_style)
    logger.info("开始下载验证码图片(1): " + img1_url)
    download_image(img1_url, "captcha.jpg")
    sprite = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="instruction"]/div/img')))
    img2_url = sprite.get_attribute("src")
    logger.info("开始下载验证码图片(2): " + img2_url)
    download_image(img2_url, "sprite.jpg")


def process_captcha(driver, wait):
    try:
        download_captcha_img(wait)
        if check_captcha():
            logger.info("开始识别验证码")
            captcha = cv2.imread("temp/captcha.jpg")
            with open("temp/captcha.jpg", 'rb') as f:
                captcha_b = f.read()
            bboxes = det.detection(captcha_b)
            result = {}
            for i in range(len(bboxes)):
                x1, y1, x2, y2 = bboxes[i]
                spec = captcha[y1:y2, x1:x2]
                cv2.imwrite(f"temp/spec_{i + 1}.jpg", spec)
                for j in range(3):
                    similarity, matched = compute_similarity(f"temp/sprite_{j + 1}.jpg", f"temp/spec_{i + 1}.jpg")
                    similarity_key = f"sprite_{j + 1}.similarity"
                    position_key = f"sprite_{j + 1}.position"
                    if similarity_key in result:
                        if float(result[similarity_key]) < similarity:
                            result[similarity_key] = similarity
                            result[position_key] = f"{int((x1 + x2) / 2)},{int((y1 + y2) / 2)}"
                    else:
                        result[similarity_key] = similarity
                        result[position_key] = f"{int((x1 + x2) / 2)},{int((y1 + y2) / 2)}"
            if check_answer(result):
                for i in range(3):
                    position = result[f"sprite_{i + 1}.position"]
                    logger.info(f"图案 {i + 1} 位于 ({position})，匹配率：{result[f'sprite_{i + 1}.similarity']}")
                    slideBg = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="slideBg"]')))
                    style = slideBg.get_attribute("style")
                    x, y = map(int, position.split(","))
                    width_raw, height_raw = captcha.shape[1], captcha.shape[0]
                    width = float(get_width_from_style(style))
                    height = float(get_height_from_style(style))
                    x_offset, y_offset = -width / 2, -height / 2
                    final_x = int(x_offset + x / width_raw * width)
                    final_y = int(y_offset + y / height_raw * height)
                    ActionChains(driver).move_to_element_with_offset(slideBg, final_x, final_y).click().perform()
                confirm = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tcStatus"]/div[2]/div[2]/div/div')))
                logger.info("提交验证码")
                confirm.click()
                time.sleep(5)
                result_elem = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="tcOperation"]')))
                if result_elem.get_attribute("class") == 'tc-opera pointer show-success':
                    logger.info("验证码通过")
                    return True
                else:
                    logger.error("验证码未通过")
                    return False
            else:
                logger.error("验证码识别结果重复，可能失败")
                return False
        else:
            logger.error("当前验证码识别率低，尝试刷新")
            reload = driver.find_element(By.XPATH, '//*[@id="reload"]')
            time.sleep(2)
            reload.click()
            time.sleep(3)
            return process_captcha(driver, wait)
    except TimeoutException:
        logger.error("获取验证码图片失败")
        return False


def run_sign_in(user, pwd):
    """执行单个账号的签到流程"""
    global ocr, det  # 使用全局初始化的 OCR 实例
    logger.info(f"开始处理账号: {user}")
    driver = None
    try:
        driver = init_selenium()
        # 注入反检测脚本
        if os.path.exists("stealth.min.js"):
            with open("stealth.min.js", mode="r") as f:
                js = f.read()
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": js})
        else:
            logger.warning("未找到 stealth.min.js，可能被检测")

        wait = WebDriverWait(driver, TIMEOUT)
        logger.info("发起登录请求")
        driver.get("https://app.rainyun.com/auth/login")

        username = wait.until(EC.visibility_of_element_located((By.NAME, 'login-field')))
        password = wait.until(EC.visibility_of_element_located((By.NAME, 'login-password')))
        login_button = wait.until(EC.visibility_of_element_located((By.XPATH,
                                                                    '//*[@id="app"]/div[1]/div[1]/div/div[2]/fade/div/div/span/form/button')))
        username.send_keys(user)
        password.send_keys(pwd)
        login_button.click()

        # 检查是否触发登录验证码
        try:
            login_captcha = wait.until(EC.visibility_of_element_located((By.ID, 'tcaptcha_iframe_dy')))
            logger.warning("触发登录验证码！")
            driver.switch_to.frame("tcaptcha_iframe_dy")
            success = process_captcha(driver, wait)
            driver.switch_to.default_content()
            if not success:
                raise Exception("登录验证码未通过")
        except TimeoutException:
            logger.info("登录未触发验证码")

        if driver.current_url != "https://app.rainyun.com/dashboard":
            raise Exception("登录失败：未跳转到仪表盘")

        logger.info("登录成功！正在转到赚取积分页")
        driver.get("https://app.rainyun.com/account/reward/earn")
        driver.implicitly_wait(5)

        earn = driver.find_element(By.XPATH,
                                   '//*[@id="app"]/div[1]/div[3]/div[2]/div/div/div[2]/div[2]/div/div/div/div[1]/div/div[1]/div/div[1]/div/span[2]/a')
        logger.info("点击赚取积分")
        earn.click()

        # 处理签到验证码
        driver.switch_to.frame("tcaptcha_iframe_dy")
        success = process_captcha(driver, wait)
        driver.switch_to.default_content()
        if not success:
            raise Exception("签到验证码未通过")

        driver.implicitly_wait(5)
        points_raw = driver.find_element(By.XPATH,
                                         '//*[@id="app"]/div[1]/div[3]/div[2]/div/div/div[2]/div[1]/div[1]/div/p/div/h3').get_attribute(
            "textContent")
        current_points = int(''.join(re.findall(r'\d+', points_raw)))
        logger.info(f"账号 {user} 签到成功！当前积分: {current_points} | 约为 {current_points / 2000:.2f} 元")
        send_dingtalk_message(f"【雨云签到成功】\n账号: {user}\n当前积分: {current_points} 分\n约合 ¥{current_points / 2000:.2f}")
        return True

    except Exception as e:
        error_msg = f"账号 {user} 签到失败: {str(e)}"
        logger.error(error_msg)
        send_dingtalk_message(f"【雨云签到失败】\n账号: {user}\n错误: {str(e)[:100]}")
        return False
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("------------------------------------------------------------------")
    logger.info(f"雨云多账号签到工具 v{VER} by SerendipityR ~")
    logger.info("支持多账号自动签到")
    logger.info("------------------------------------------------------------------")

    # 初始化 OCR（只需一次）
    logger.info("初始化 ddddocr")
    ocr = ddddocr.DdddOcr(ocr=True, show_ad=False)
    det = ddddocr.DdddOcr(det=True, show_ad=False)

    # 随机延迟（仅非调试模式）
    if not DEBUG:
        delay = random.randint(0, MAX_DELAY)
        delay_sec = random.randint(0, 60)
        logger.info(f"随机延时等待 {delay} 分钟 {delay_sec} 秒")
        time.sleep(delay * 60 + delay_sec)

    # 遍历所有账号
    results = []
    for account in ACCOUNTS:
        user = account["user"]
        pwd = account["pwd"]
        try:
            success = run_sign_in(user, pwd)
            results.append((user, success))
        except Exception as e:
            logger.exception(f"账号 {user} 执行异常: {e}")
            results.append((user, False))
        # 账号之间间隔几秒，避免请求过快
        time.sleep(5)

    # 汇总结果
    success_count = sum(1 for _, ok in results if ok)
    total = len(ACCOUNTS)
    logger.info(f"多账号签到完成：{success_count}/{total} 成功")