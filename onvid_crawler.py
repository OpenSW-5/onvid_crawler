"""
온비드 동산·기타자산 입찰결과 크롤러  (수동 로그인 → 자동 수집)
────────────────────────────────────────────────────────────────────
기간  : 2015 ~ 2024
컬럼  : 일련번호, 기관/담당부점, 카테고리, 물건정보,
        최저입찰가, 낙찰가, 낙찰가율, 입찰결과, 개찰일시
출력  : 2015.csv … 2024.csv
사용 절차
  ① 실행 → 브라우저에서 로그인(캡챠 포함)
  ② 메뉴 ‘동산/기타자산 ▸ 입찰결과’ 진입
  ③ 터미널에 ENTER → 연도별 자동 수집 시작
────────────────────────────────────────────────────────────────────
"""

import csv, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ─────────── Chrome 옵션 ───────────
options = webdriver.ChromeOptions()
# options.add_argument("--headless")          # ↙ 화면 보면서 디버깅할 때만 주석
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-popup-blocking")
options.add_argument("--window-size=1920,1080")
options.add_argument(
    "--disable-features=SameSiteByDefaultCookies,CookiesWithoutSameSiteMustBeSecure"
)

driver = webdriver.Chrome(options=options)
wait   = WebDriverWait(driver, 20)

LIST_URL = "https://www.onbid.co.kr/op/bda/bidrslt/moveableResultList.do"

# ─────────── ① 수동 로그인 ───────────
def manual_login_once() -> None:
    driver.get("https://www.onbid.co.kr/op/mba/loginmn/loginForm.do")
    print("\n▶ 브라우저가 열렸습니다!")
    print("   1) 아이디/비밀번호 + 캡차 입력 → 로그인")
    print("   2) 상단 ‘동산/기타자산 ▸ 입찰결과’ 접속")
    input("결과 목록 화면이 뜨면 ENTER ▶ ")
    driver.get(LIST_URL)          # 혹시 사용자가 다른 페이지에 있으면 강제 이동

# ─────────── ② 검색 기간 설정 ───────────
def set_year_range(year: int) -> None:
    wait.until(EC.element_to_be_clickable((By.ID, "searchBidDateFrom")))
    driver.find_element(By.ID, "searchBidDateFrom").clear()
    driver.find_element(By.ID, "searchBidDateFrom").send_keys(f"{year}-01-01")
    driver.find_element(By.ID, "searchBidDateTo").clear()
    driver.find_element(By.ID, "searchBidDateTo").send_keys(f"{year}-12-31")
    driver.find_element(By.ID, "searchBtn").click()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))

# ─────────── ③ 상세보기 파싱 ───────────
def grab_org_or_dept(detail_anchor) -> str:
    """상세보기 <a> 클릭 → 새 탭으로 뜨는 상세 팝업에서 기관/담당부점 추출"""
    parent = driver.current_window_handle
    driver.execute_script("arguments[0].click();", detail_anchor)

    try:
        # 새 탭이 열릴 때까지 대기
        wait.until(lambda d: len(d.window_handles) > 1)
    except TimeoutException:
        return "정보 없음"

    driver.switch_to.window(driver.window_handles[-1])

    # about:blank → 실제 URL 로 바뀔 때까지 3초 한도 대기
    for _ in range(30):
        if driver.current_url != "about:blank":
            break
        time.sleep(0.1)

    try:
        lbl = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//th[contains(text(),'기관명') or contains(text(),'담당부점')]")
            )
        )
        value = driver.find_element(
            By.XPATH,
            "//th[contains(text(),'기관명') or contains(text(),'담당부점')]/following-sibling::td"
        ).text.strip() or "정보 없음"
    except Exception:
        value = "정보 없음"

    driver.close()
    driver.switch_to.window(parent)
    return value

# ─────────── ④ 연도별 수집 ───────────
def crawl_one_year(writer) -> None:
    page = 1
    while True:
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        if not rows:
            break

        for row in rows:
            tds        = row.find_elements(By.TAG_NAME, "td")
            serial_e   = row.find_elements(By.CSS_SELECTOR, "dl.info dt a")
            item_e     = row.find_elements(By.CSS_SELECTOR, "em.fwb")
            if not (serial_e and item_e and len(tds) >= 6):
                continue  # 필수 필드 누락

            serial = serial_e[0].text.strip()
            item   = item_e[0].text.strip()
            if not item:
                continue

            category_e = row.find_elements(By.CSS_SELECTOR, "p.tpoint_03")
            category   = category_e[0].text.strip() if category_e else "정보 없음"

            min_price, final_price, bid_rate, bid_result, bid_date = [
                td.text.strip() for td in tds[1:6]
            ]

            # 상세보기 <a> (onclick: fn_openDetailView)
            detail_a = row.find_element(By.CSS_SELECTOR, "a[onclick*='fn_openDetailView']")
            org_dept = grab_org_or_dept(detail_a)

            writer.writerow([
                serial, org_dept, category, item,
                min_price, final_price, bid_rate, bid_result, bid_date
            ])

        # ─ 페이지 넘기기 (사이트 내 JS 함수 호출)
        page += 1
        try:
            driver.execute_script(f"fn_paging('{page}')")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
        except Exception:
            break

# ─────────── ⑤ 메인 루틴 ───────────
def main():
    manual_login_once()

    for year in range(2015, 2025):     # 2024 포함
        print(f"\n📆 {year}년 데이터 수집 중 …")
        set_year_range(year)

        with open(f"{year}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "일련번호", "기관/담당부점", "카테고리", "물건정보",
                "최저입찰가(원)", "낙찰가(원)", "낙찰가율(%)",
                "입찰결과", "개찰일시"
            ])
            crawl_one_year(writer)

        print(f"✅ {year}.csv 저장 완료")

    driver.quit()

# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
