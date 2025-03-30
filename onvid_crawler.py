import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# 로그인 정보 (보안상 환경 변수로 관리 권장)
ONBID_ID = "YOUR_ID"
ONBID_PW = "YOUR_PASS"

# 웹드라이버 설정
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # 필요하면 주석 처리
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# 웹드라이버 실행
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

def login_onbid():
    driver.get("https://www.onbid.co.kr/op/mba/loginmn/loginForm.do")  # 로그인 페이지 URL
    time.sleep(2)
    
    # ID 입력
    id_input = driver.find_element(By.ID, "usrId")
    id_input.send_keys(ONBID_ID)
    
    # PW 입력
    pw_input = driver.find_element(By.ID, "encpw")
    pw_input.send_keys(ONBID_PW)
    pw_input.send_keys(Keys.RETURN)
    
    time.sleep(3)  # 로그인 완료 대기
    print("로그인 완료")

def scrape_bid_results():
    driver.get("https://www.onbid.co.kr/op/bda/bidrslt/moveableResultList.do")  # 입찰 결과 페이지 URL
    time.sleep(3)
    
    # CSV 파일 초기화
    with open('onvid_data.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # 헤더 작성
        writer.writerow(['물건정보', '최저입찰가 (예정가격)(원)', '낙찰가(원)', '낙찰가율(%)', '입찰결과', '개찰일시'])

        # 페이지 번호 변수 초기화
        current_page_number = 1

        def fn_paging(page_number):
            """페이지 번호를 받아서 해당 페이지로 이동하는 함수"""
            driver.execute_script(f"fn_paging('{page_number}')")

        while True:  # 페이지 이동을 위한 루프
            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            
            for row in rows:
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    
                    # 데이터 개수가 부족하거나, 모든 값이 '정보 없음'인 경우 스킵
                    if len(cols) < 6:
                        continue

                    item_info_elem = row.find_elements(By.CSS_SELECTOR, "em.fwb")  # 물건정보
                    item_info = item_info_elem[0].text.strip() if item_info_elem else "정보 없음"
                    
                    # 물건 정보가 '정보 없음'이면 해당 행을 스킵
                    if item_info == "정보 없음":
                        continue

                    min_bid_price = cols[1].text.strip() if len(cols) > 1 else "정보 없음"  # 최저입찰가
                    final_bid_price = cols[2].text.strip() if len(cols) > 2 else "정보 없음"  # 낙찰가
                    bid_rate = cols[3].text.strip() if len(cols) > 3 else "정보 없음"  # 낙찰가율
                    bid_result = cols[4].text.strip() if len(cols) > 4 else "정보 없음"  # 입찰결과
                    
                    # 개찰일시에서 "상세보기" 같은 불필요한 데이터 필터링
                    bid_date = cols[5].text.strip() if len(cols) > 5 and "상세보기" not in cols[5].text else "정보 없음"

                    # CSV 파일에 수집된 데이터 저장
                    writer.writerow([item_info, min_bid_price, final_bid_price, bid_rate, bid_result, bid_date])

                except Exception as e:
                    print("데이터 수집 오류:", e)

            # 페이지 번호를 +1 하여 다음 페이지로 이동
            try:
                current_page_number += 1  # 페이지 번호 증가

                # fn_paging 함수 호출하여 페이지 변경
                fn_paging(current_page_number)  # 페이지 번호를 함수에 전달하여 페이지 이동

                time.sleep(3)  # 페이지 로딩 대기

            except Exception as e:
                print("다음 페이지로 이동하는 도중 오류 발생:", e)
                break  # 오류가 발생하면 종료


if __name__ == "__main__":
    login_onbid()
    scrape_bid_results()
    driver.quit()
