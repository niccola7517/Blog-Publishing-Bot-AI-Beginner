import os
import sys
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from google import genai

def run_curator():
    print("--- [Trend Topic Curator] 파이프라인 시작 ---")
    
    # 1. 환경 변수 및 API Key 로드
    api_key = os.environ.get("AI_API_KEY")
    service_account_json = os.environ.get("GCP_SA_KEY")
    
    if not api_key:
        print("❌ AI_API_KEY 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)
    if not service_account_json:
        print("❌ GCP_SA_KEY 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)

    # 2. Google Sheets & Drive API 인증
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        eval(service_account_json), scopes=scopes
    )
    gc = gspread.authorize(credentials)

    # ==========================================
    # 1단계: Google Drive 'AI 키워드' 검색 및 데이터 추출
    # ==========================================
    spreadsheet_name = "AI 키워드"
    try:
        sh = gc.open(spreadsheet_name)
        worksheet = sh.sheet1
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ Google Drive에서 '{spreadsheet_name}' 파일을 찾을 수 없습니다.")
        sys.exit(1)

    records = worksheet.get_all_records()
    target_row_index = -1
    target_keyword = ""

    # '퍼블리싱여부' 컬럼이 'N'인 가장 첫 번째 행 찾기
    for idx, row in enumerate(records):
        publishing_status = str(row.get("퍼블리싱여부", "")).strip().upper()
        if publishing_status == "N":
            target_row_index = idx + 2  # 헤더가 1행이므로 데이터는 2행부터 시작
            target_keyword = row.get("핵심키워드", "")
            break

    if target_row_index == -1:
        print("Google Sheets의 'AI 키워드' 문서에 처리할 미발행('N') 키워드가 없습니다.")
        sys.exit(0)

    # ==========================================
    # 2단계: 입문자 맞춤형 4가지 주제 큐레이션
    # ==========================================
    client = genai.Client(api_key=api_key)
    prompt = f"""
    당신은 비전공자 및 IT/AI 입문자를 위한 테크 블로그 전문 큐레이터입니다.
    쉬운 일상 비유와 실무/생산성 중심의 친근한 톤앤매너로 아래 핵심키워드에 대한 4가지 블로그 주제를 작성해 주세요.

    - 타겟 핵심키워드: {target_keyword}

    [필수 구성]
    - Topic 1 [개념 이해]: 직관적인 일상 비유로 풀어낸 기술의 본질과 등장 배경
    - Topic 2 [실무 활용]: 비개발자 직장인이 업무/일상에서 바로 써먹는 생산성 향상 사례
    - Topic 3 [입문 튜토리얼]: 웹 브라우저 기반 무료 도구로 10분 만에 끝내는 0 to 1 실습 가이드
    - Topic 4 [트러블슈팅 & 꿀팁]: 에러 발생 시 대화 요령, 초보자 주의사항 및 보안 수칙

    각 주제마다 '제목, 타겟 훅, 주요 내용, 기대 효과'를 포함하여 깔끔하게 정리해 주세요.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    curated_topics = response.text

    # ==========================================
    # 3단계: 상태 업데이트 ('N' -> 'Y') 및 날짜별 신규 파일 생성
    # ==========================================
    # 3-1. 원본 시트 상태 'Y'로 업데이트
    header_row = worksheet.row_values(1)
    if "퍼블리싱여부" in header_row:
        status_col_idx = header_row.index("퍼블리싱여부") + 1
        worksheet.update_cell(target_row_index, status_col_idx, "Y")

    # 3-2. 오늘 날짜가 포함된 새 버전의 Google Sheets 저장 (중복 시 v2, v3 처리)
    today_str = datetime.now().strftime("%Y-%m-%d")
    base_title = f"[{today_str}] AI 키워드"
    new_sheet_title = base_title
    
    counter = 1
    while True:
        try:
            # 중복 이름 확인
            gc.open(new_sheet_title)
            counter += 1
            new_sheet_title = f"{base_title} (v{counter})"
        except gspread.exceptions.SpreadsheetNotFound:
            break

    # 원본 파일 전체를 복사하여 새 파일 생성
    new_sh = gc.copy(sh.id, title=new_sheet_title)

    # ==========================================
    # 4단계: 결과 안내 및 선택 대기
    # ==========================================
    print("\n==========================================")
    print(f"🎯 핵심키워드: {target_keyword}")
    print("==========================================\n")
    print(curated_topics)
    print("\n==========================================")
    print(f"✅ 상태 'Y'로 갱신 완료")
    print(f"📁 새 버전 시트 생성됨: {new_sheet_title}")
    print(f"🔗 문서 링크: https://docs.google.com/spreadsheets/d/{new_sh.id}")
    print("\n작성할 주제 번호를 선택해 주세요 (다중 선택 가능)")
    print("==========================================\n")

if __name__ == "__main__":
    run_curator()