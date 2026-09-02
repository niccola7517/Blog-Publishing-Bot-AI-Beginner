import os
import json
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google import genai
from google.genai import types

def run_publisher():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"--- [AEO Daily Docs Publisher] 파이프라인 시작 ({today_str}) ---")
    
    # 1. 환경 변수 확인 (GitHub Secrets와 연동)
    api_key = os.environ.get("AI_API_KEY")
    service_account_json = os.environ.get("GCP_SA_KEY")
    
    if not api_key:
        raise ValueError("AI_API_KEY 환경 변수가 설정되지 않았습니다.")

    # 2. 로컬 저장소(docs) 폴더 확인 및 생성
    docs_dir = "docs"
    os.makedirs(docs_dir, exist_ok=True)
    
    # 오늘 날짜의 HTML 파일명 정의
    html_file_name = f"{today_str}_Cloud-AI_테크포스팅.html"
    local_file_path = os.path.join(docs_dir, html_file_name)

    # 3. Gemini API를 통한 구조화된 HTML 생성 (스킬의 철학 및 포맷 엄수)
    client = genai.Client(api_key=api_key)
    
    # 이전 단계(curator)에서 전달받은 주제가 있다고 가정 (여기서는 임시 데이터 처리)
    # 실제 연동 시 시트에서 큐레이션된 데이터를 읽어오도록 확장할 수 있습니다.
    target_keyword = "테스트 클라우드 키워드"
    
    topics = [
        f"{target_keyword} - [개념 이해]: 직관적인 일상 비유로 풀어낸 기술의 본질과 등장 배경",
        f"{target_keyword} - [실무 활용]: 비개발자 직장인이 업무/일상에서 바로 써먹는 생산성 향상 사례",
        f"{target_keyword} - [입문 튜토리얼]: 웹 브라우저 기반 무료 도구로 10분 만에 끝내는 0 to 1 실습 가이드",
        f"{target_keyword} - [트러블슈팅 & 꿀팁]: 에러 발생 시 대화 요령, 초보자 주의사항 및 보안 수칙"
    ]
    
    generated_results = []
    
    for i, topic_name in enumerate(topics, 1):
        print(f"[{today_str}] Topic {i} 생성 중... ({topic_name})")
        prompt = f"""
        당신은 AEO/GEO 최적화 기술 블로그 포스팅 전문가입니다.
        초보자와 비전공자(Complete beginners)를 대상으로 다음 주제에 대한 기술 블로그 포스팅을 HTML 형식으로 작성해 주세요.
        
        주제: {topic_name}
        
        [엄격한 작성 규칙 - Blogspot 최적화]
        1. 형식: <html>, <head>, <body> 같은 문서 래퍼 태그를 절대 쓰지 마세요. <h2>, <h3>, <p>, <ul> 등의 본문 태그만 출력해야 Blogger 'HTML 보기' 모드에 바로 붙여넣을 수 있습니다.
        2. Tone: 복잡한 기술 개념을 일상적인 비유(metaphors)로 설명하고 실무/일상적 가치에 집중하세요.
        3. Heading: 최상단 제목은 <h2>로 시작하고, 하위 항목은 <h3>를 사용하세요. (블로그스팟은 글 제목이 h1이 되므로 본문은 h2부터 시작하는 것이 SEO에 좋습니다)
        4. Body: 모바일 가독성을 위해 문단(<p>)을 짧게 끊고, 여백(<br><br>)을 적절히 활용하세요.
        5. Table: <th> 1줄을 포함한 단일 헤더 비교 표를 깔끔한 인라인 CSS와 함께 작성하세요.
        6. FAQ: 문서 하단에 <h3>FAQ</h3>를 만들고 자주 묻는 질문 3개를 작성하세요.
        7. 분량: 최소 2,000자 이상으로 풍성하게 작성하세요.
        """

        response = client.models.generate_content(
            model='gemini-3.7-flash', # 복잡한 구조화 지시가 있으므로 성능이 좋은 최신 flash 모델 사용
            contents=prompt,
        )
        article_html = response.text
        char_count = len(article_html)
        generated_results.append((topic_name, article_html, char_count))

    # 6. 로컬 HTML 파일로 저장 (Blogspot 용)
    # 기존 파일이 있다면 뒤에 이어쓰고(append), 없으면 새로 만듭니다.
    with open(local_file_path, "a", encoding="utf-8") as f:
        for i, (topic_name, article_html, char_count) in enumerate(generated_results, 1):
            f.write(f"<!-- Topic {i}: {topic_name} -->\n")
            f.write(article_html)
            f.write("\n\n<hr style='border: 1px solid #eee; margin: 40px 0;'>\n\n")

    # 7. 출력 규칙 (Output & Verification) 준수
    print(f"\n✅ [{today_str}] Cloud-AI 테크 포스팅 작성이 완료되었습니다.")
    print(f"📁 저장 위치: GitHub 저장소의 {local_file_path}")
    print("\n[생성된 주제 요약]")
    for i, (topic_name, article_html, char_count) in enumerate(generated_results, 1):
        print(f"- Topic {i}: {topic_name} (약 {char_count}자)")
    print("\n👉 다음 단계로 썸네일을 생성하려면 아래 명령어를 입력하세요:")
    print("/aeo-thumbnail-generator 1 2 3 4\n")

if __name__ == "__main__":
    run_publisher()