import os
import time
import traceback

# 尝试导入winsound库，用于声音提醒，如果不是Windows系统则忽略
try:
    import winsound
except ImportError:
    winsound = None

# 关键新增：导入 ddddocr 用于验证码识别
try:
    import ddddocr
except ImportError:
    print("错误: ddddocr 库未安装。")
    print("请使用 'pip install ddddocr' 命令进行安装。")
    exit(1)

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions

# ---------------- 配置参数 ----------------
USERNAME = input("请输入您的用户名（学号或邮箱）: ")
PASSWORD = input("请输入您的密码: ")
COURSE_CODES = input("请输入您想抢的课程代码，多个代码请用逗号分隔: ").split(',')
COURSE_CODES = [code.strip() for code in COURSE_CODES if code.strip()]
MAX_ATTEMPTS = 100000
RETRY_DELAY = 0.1   # 保持快速刷新

# ---------------- 启动Edge浏览器 ----------------
edge_driver_path = r"./msedgedriver.exe"
if not os.path.exists(edge_driver_path):
    print(f"错误: 在路径 {edge_driver_path} 找不到 EdgeDriver")
    exit(1)

options = EdgeOptions()
options.add_experimental_option("detach", True)
service = Service(edge_driver_path)
driver = webdriver.Edge(service=service, options=options)
print("Edge浏览器已启动 (分离模式)")
driver.implicitly_wait(10)

# ---------------- 工具函数 ----------------
def recognize_captcha(image_element, input_element):
    ocrImage = driver.find_element(By.ID, image_element)
    ocrImage.screenshot('ocrCal.png')
    ocr = ddddocr.DdddOcr()
    with open('ocrCal.png', 'rb') as f:
        img_bytes = f.read()
    result = ocr.classification(img_bytes)
    vcode_input = driver.find_element(By.ID, input_element)
    vcode_input.clear()
    vcode_input.send_keys(result)


def play_alert_sound():
    if winsound:
        print("正在播放声音提醒...")
        winsound.Beep(1000, 2500)
    else:
        print("当前系统不支持声音提醒。")



# ---------------- 登录相关 ----------------
def login():
    driver.get("https://sep.ucas.ac.cn/")
    print("已访问SEP网站")
    username_input = driver.find_element(By.ID, 'userName1')
    password_input = driver.find_element(By.ID, 'pwd1')
    username_input.send_keys(USERNAME)
    password_input.send_keys(PASSWORD)
    # recognize_captcha('code', 'certCode1')
    login_button = driver.find_element(By.ID, 'sb1')
    login_button.click()
    print("已尝试登录")

    wait = WebDriverWait(driver, 20)
    xuankexitong = wait.until(EC.presence_of_element_located((By.LINK_TEXT, '选课系统')))
    xuankexitong.click()
    print("已点击选课系统")

    driver.switch_to.window(driver.window_handles[-1])
    print("已切换到新窗口")

    xinzeng = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '新增加本学期研究生课程')]"))
    )
    xinzeng.click()
    print("已进入选课查询页面")

# ---------------- 课程操作 ----------------
def check_and_select_course(course_code):
    try:

        course_code_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "courseCode"))
        )

        course_code_input.clear()
        course_code_input.send_keys(course_code)
        # print("输入课程代码  OK")
        query_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'查询')]"))
        )
        # print("找到查询按钮  OK")
        query_button.click()
        # print("点击查询按钮  OK")
        checkbox = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, "sids"))
        )
        # print("找到选课框  OK")
        if checkbox.get_attribute("disabled"):
            # print(f"课程 {course_code} 仍然已满。")
            return False
        else:
            print(f"!!! 发现课程 {course_code} 有空位，正在尝试勾选... !!!")
            checkbox.click()
            print("点击选课框  OK")
            print(f"✅ 已成功为您勾选课程: {course_code}")
            return True

    except Exception:
        # print(f"查询课程 {course_code} 时未找到可选框，判定为已满。")
        driver.refresh()
        # 刷新后检查是否还在选课页面
        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.ID, "courseCode"))
            )
        except:
            print("检测到掉线，正在重新登录...")
            login()
        return False

# ---------------- 主程序 ----------------
try:
    login()

    print("正在初始化验证码识别模块...")
    ocr = ddddocr.DdddOcr(show_ad=False)
    print("验证码识别模块初始化完成。")

    attempt_count = 0
    course_selected_and_submitted = False

    while not course_selected_and_submitted and attempt_count < MAX_ATTEMPTS:
        attempt_count += 1
        print(f"\n===== 第 {attempt_count} 轮监控 =====")

        for code in COURSE_CODES:
            if check_and_select_course(code):
                try:
                    print("课程已勾选，开始处理验证码并提交...")
                    ocrImage = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, 'adminValidateImg'))
                    )
                    img_bytes = ocrImage.screenshot_as_png
                    result = ocr.classification(img_bytes)
                    print(f"验证码识别结果: {result}")

                    vcode_input = driver.find_element(By.ID, 'vcode')
                    vcode_input.clear()
                    vcode_input.send_keys(result)

                    submit_button = driver.find_element(By.ID, 'submitCourse')
                    submit_button.click()
                    print("已点击“提交选课”按钮。")

                    confirm_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[@class='jbox-button' and @value='ok']"))
                    )
                    confirm_button.click()

                    print("\n" + "#" * 60)
                    print("###                                            ###")
                    print("###     🎉🎉🎉 选课成功并已自动提交！🎉🎉🎉     ###")
                    print("###                                            ###")
                    print("#" * 60)

                    course_selected_and_submitted = True
                    play_alert_sound()
                    break

                except Exception as submit_error:
                    print(f"提交课程 {code} 时发生错误: {submit_error}")
                    print("可能是验证码识别错误或网络延迟。正在刷新页面后继续监控...")
                    driver.refresh()
                    try:
                        WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.ID, "courseCode"))
                        )
                    except:
                        print("检测到掉线，正在重新登录...")
                        login()

        if course_selected_and_submitted:
            break

        print(f"本轮监控结束，未发现空位或提交失败。将在 {RETRY_DELAY} 秒后开始下一轮...")
        time.sleep(RETRY_DELAY)

    print("\n----------------------------------------------------")
    if course_selected_and_submitted:
        print("任务完成。脚本即将关闭，浏览器将保持打开状态供您确认。")
    else:
        print(f"达到最大尝试次数 {MAX_ATTEMPTS}，未抢到课程。脚本即将关闭。")
    print("----------------------------------------------------")

except Exception as e:
    print(f"发生致命错误: {e}")
    traceback.print_exc()