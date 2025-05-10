"""
온비드 과거 동산 입찰결과 크롤러
 - 기간: 2015 ~ 2024 (1년 단위)
 - 컬럼: 일련번호, 카테고리, 물건정보, 최저입찰가, 낙찰가, 낙찰가율, 입찰결과, 개찰일시
 - 결과: 2015.csv, 2016.csv, … , 2024.csv
"""

import csv, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# ──────────────────────────────────────────────────────────────
# ① 로그인 정보
ONBID_ID = "YOUR_ID"
ONBID_PW = "YOUR_PASS"

# ② 드라이버 세팅
options = webdriver.ChromeOptions()
options.add_argument("--headless")          # 디버깅 시 주석 처리
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)
wait = WebDriverWait(driver, 10)

# ──────────────────────────────────────────────────────────────
def login_onbid() -> None:
    """온비드 로그인"""
    driver.get("https://www.onbid.co.kr/op/mba/loginmn/loginForm.do")
    wait.until(EC.presence_of_element_located((By.ID, "usrId")))

    driver.find_element(By.ID, "usrId").send_keys(ONBID_ID)
    pw = driver.find_element(By.ID, "encpw")
    pw.send_keys(ONBID_PW)
    pw.send_keys(Keys.RETURN)

    # 바로 결과 페이지로 이동해 입력창 등장 여부로 로그인 확인
    driver.get("https://www.onbid.co.kr/op/bda/bidrslt/moveableResultList.do")
    try:
        wait.until(EC.presence_of_element_located((By.ID, "searchBidDateFrom")))
        print("로그인 및 페이지 로딩 완료")
    except TimeoutException:
        print("로그인 확인 타임아웃 → 5초 대기 후 계속 진행")
        time.sleep(5)

# ──────────────────────────────────────────────────────────────
def set_date_range(from_date: str, to_date: str) -> None:
    """검색 기간(개찰일시) 설정 후 검색"""
    wait.until(EC.presence_of_element_located((By.ID, "searchBidDateFrom")))
    from_box = driver.find_element(By.ID, "searchBidDateFrom")
    to_box   = driver.find_element(By.ID, "searchBidDateTo")

    from_box.clear();  from_box.send_keys(from_date)
    to_box.clear();    to_box.send_keys(to_date)

    driver.find_element(By.ID, "searchBtn").click()
    # 결과 테이블 로딩 대기
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))

# ──────────────────────────────────────────────────────────────
def extract_serial(row) -> str:
    """
    <dl class="info"> → <dt> → <a> 순으로 일련번호 추출.
    없으면 '정보 없음' 반환.
    """
    a_tags = row.find_elements(By.CSS_SELECTOR, "dl.info dt a")
    if a_tags and a_tags[0].text.strip():
        return a_tags[0].text.strip()
    return "정보 없음"

# ──────────────────────────────────────────────────────────────
def scrape_current_search(writer) -> None:
    """현재 검색 결과(1년치)에 대해 모든 페이지 순회하며 데이터 저장"""
    page = 1
    while True:
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        if not rows:
            break

        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            if len(tds) < 6:
                continue

            serial_num = extract_serial(row)                       # 일련번호
            cat_elem = row.find_elements(By.CSS_SELECTOR, "p.tpoint_03")
            category = cat_elem[0].text.strip() if cat_elem else "정보 없음"

            item_elem = row.find_elements(By.CSS_SELECTOR, "em.fwb")
            item_info = item_elem[0].text.strip() if item_elem else "정보 없음"
            if item_info == "정보 없음":
                continue  # 공백 행 스킵

            min_bid_price   = tds[1].text.strip()
            final_bid_price = tds[2].text.strip()
            bid_rate        = tds[3].text.strip()
            bid_result      = tds[4].text.strip()
            bid_date        = (tds[5].text.strip()
                               if "상세보기" not in tds[5].text else "정보 없음")

            writer.writerow([
                serial_num, category, item_info,
                min_bid_price, final_bid_price,
                bid_rate, bid_result, bid_date
            ])

        # ─── 다음 페이지 이동 ───
        page += 1
        try:
            driver.execute_script(f"fn_paging('{page}')")
            time.sleep(1.5)   # 짧은 로딩 대기
        except Exception:
            break             # 마지막 페이지면 빠져나옴

# ──────────────────────────────────────────────────────────────
def main(): 
    login_onbid()

    for year in range(2015, 2024): 
        from_date = f"{year}-01-01"
        to_date   = f"{year}-12-31"
        print(f"\n📆 {year}년 ({from_date} ~ {to_date}) 수집 시작")

        set_date_range(from_date, to_date)

        csv_name = f"{year}.csv"
        with open(csv_name, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "일련번호", "카테고리", "물건정보",
                "최저입찰가 (예정가격)(원)", "낙찰가(원)",
                "낙찰가율(%)", "입찰결과", "개찰일시"
            ])
            scrape_current_search(writer)

        print(f"✅ {csv_name} 저장 완료")

    driver.quit()

# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
 