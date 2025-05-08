from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import time
import random

# 配置 Chrome 浏览器选项
chrome_options = Options()
# chrome_options.add_argument('--headless')  # 暂时注释掉无头模式
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
chrome_options.add_argument('--incognito')  # 无痕模式

# 显式指定 ChromeDriver 路径，将这里替换为你实际的路径
driver_path = 'C:/Program Files/chromedriver.exe'
from selenium.webdriver.chrome.service import Service
service = Service(driver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

url = 'https://www.hltv.org/ranking/teams/2025/may/5'
try:
    print("正在打开页面...")
    driver.get(url)
    print("页面已打开，开始处理 Cookie 弹窗...")

    # 处理 Cookie 弹窗
    try:
        # 等待按钮可点击，使用 id 定位
        allow_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, 'CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll'))
        )
        print("找到 Cookie 按钮，准备点击...")
        allow_button.click()
        print("Cookie 按钮点击成功")
        # time.sleep(random.uniform(3, 8))  # 点击 Cookie 按钮后随机等待 3 - 8 秒
    except Exception as e:
        print(f"点击 Cookie 按钮出错: {e}")
        # 输出页面源码用于调试
        with open('page_source.html', 'w', encoding='utf - 8') as f:
            f.write(driver.page_source)

    print("处理完 Cookie 弹窗，检查是否有真人验证窗口...")
    try:
        print("开始等待包含验证复选框的 iframe 出现...")
        iframe = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[title="Cloudflare"]'))
        )
        driver.switch_to.frame(iframe)
        print("已切换到包含验证复选框的 iframe")
        print("开始等待复选框可点击...")
        verify_checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//input[@type="checkbox" and @aria-label="确认您是真人"]'))
        )
        time.sleep(random.uniform(1, 3))  # 点击复选框前随机等待 1 - 3 秒
        verify_checkbox.click()
        print("已点击真人验证复选框")
        driver.switch_to.default_content()
        time.sleep(random.uniform(3, 5))  # 切换回主页面后随机等待 3 - 5 秒
    except Exception as e:
        print(f"未找到真人验证窗口或处理出错: {e}")
        driver.switch_to.default_content()  # 确保回到主页面

    print("等待页面元素加载...")
    try:
        print("开始等待排名前 30 的战队元素加载...")
        elements = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.ranked-team'))
        )
        print("元素已加载，开始解析页面...")
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        team_list = soup.find_all('div', class_='ranked-team')[:30]
        if not team_list:
            print("未找到排名前 30 的战队元素，请检查页面结构是否发生变化。")
        for team in team_list:
            # 优化战队名称元素定位，增加容错
            team_name_elem = team.find(lambda tag: tag.name =='span' and 'teamName' in tag.get('class', []))
            if team_name_elem:
                team_name = team_name_elem.text.strip()
            else:
                print("在该战队元素中未找到战队名称元素")
                team_name = "未找到战队名称"
            # 优化战队成员元素定位，增加容错
            member_elements = team.find_all(lambda tag: tag.name == 'div' and 'playerName' in tag.get('class', []))
            if member_elements:
                members = [member.text.strip() for member in member_elements]
            else:
                print("在该战队元素中未找到战队成员元素")
                members = []
            print(f"战队名称: {team_name}")
            print(f"战队成员: {', '.join(members)}\n")
    except Exception as e:
        print(f"等待战队元素加载出错: {e}")

except Exception as e:
    print(f"发生异常: {e}")
finally:
    driver.quit()