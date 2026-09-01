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
    if not service_account_json:
        raise ValueError("GCP_SA_KEY 환경 변수가 설정되지 않았습니다.")

    # 2. Google Drive & Docs API 인증 설정
    scopes = [
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        eval(service_account_json), scopes=scopes
    )
    drive_service = build('drive', 'v3', credentials=credentials)
    docs_service = build('docs', 'v1', credentials=credentials)

    # 3. 타겟 아카이브 폴더 확인 및 생성
    folder_name = "Cloud-AI 포스팅 아카이브"
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    folder_results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    folders = folder_results.get('files', [])

    if folders:
        folder_id = folders[0]['id']
    else:
        folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
        folder_id = folder.get('id')

    # 4. 일일 포스팅 문서 확인 및 생성
    doc_title = f"[{today_str}] Cloud-AI 테크 포스팅"
    doc_query = f"name='{doc_title}' and '{folder_id}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false"
    doc_results = drive_service.files().list(q=doc_query, spaces='drive', fields='files(id, name)').execute()
    docs = doc_results.get('files', [])

    is_existing = False
    if docs:
        document_id = docs[0]['id']
        is_existing = True
    else:
        doc_body = {'title': doc_title}
        doc = docs_service.documents().create(body=doc_body).execute()
        document_id = doc.get('documentId')
        
        # 새 문서를 지정된 폴더로 이동
        file = drive_service.files().get(fileId=document_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents', []))
        drive_service.files().update(
            fileId=document_id, addParents=folder_id, removeParents=previous_parents, fields='id, parents'
        ).execute()

    # 5. Gemini API를 통한 구조화된 HTML 생성 (스킬의 철학 및 포맷 엄수)
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
        
        [엄격한 작성 규칙]
        1. Tone: 복잡한 기술 개념을 일상적인 비유(metaphors)로 설명하고 실무/일상적 가치에 집중하세요.
        2. Heading: 제목은 <h1> 1회, 대단원은 <h2>, 소단원은 <h3>로 엄격히 계층화하세요.
        3. Body: 모든 본문은 순수 <p> 태그만 사용하며, 볼드체(**, <b>, <strong>)는 절대 사용하지 마세요.
        4. Table: <th> 1줄을 포함한 단일 헤더 비교 표를 작성하고, 데이터 행은 <td>만 사용하세요.
        5. FAQ: <h2>FAQ</h2> 아래에 <h3> 태그를 활용하여 초보자용 질문 3개를 작성하세요.
        6. JSON-LD: 문서 끝에 <pre> 태그로 감싼 TechArticle 및 FAQPage JSON-LD 스키마를 포함하세요.
        7. 분량: 최소 2,000자 이상으로 풍성하게 작성하세요.
        """

        response = client.models.generate_content(
            model='gemini-2.5-pro', # 복잡한 구조화 지시가 있으므로 pro 모델 권장
            contents=prompt,
        )
        article_html = response.text
        char_count = len(article_html)
        generated_results.append((topic_name, article_html, char_count))

    # 6. Google Docs 문서에 내용 삽입
    # 기존 문서가 있으면 맨 앞에 구분선(---) 추가 후 이어쓰기
    requests = []
    
    # 문서 맨 앞에 가장 마지막 토픽부터 역순으로 삽입하여 1, 2, 3, 4 순서가 되도록 함
    for i, (topic_name, article_html, char_count) in enumerate(reversed(generated_results)):
        insert_text = f"\n\n---\n\n{article_html}\n" if (is_existing or i > 0) else f"{article_html}\n"
        requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': insert_text
            }
        })

    docs_service.documents().batchUpdate(
        documentId=document_id,
        body={'requests': requests}
    ).execute()

    # 7. 즉시 종료 및 지정된 출력 규칙(Output Rule) 적용 (채팅창 과부하 방지)
    doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
    
    print(f"\n✅ [{today_str}] Cloud-AI 테크 포스팅 작성이 완료되었습니다.")
    print(f"\n📄 문서 바로가기: {doc_url}")
    print(f"📁 저장 위치: {folder_name}")
    print("\n[생성된 주제 요약]")
    for i, (topic_name, article_html, char_count) in enumerate(generated_results, 1):
        print(f"- Topic {i}: {topic_name} (약 {char_count}자)")
    print("\n👉 다음 단계로 썸네일을 생성하려면 아래 명령어를 입력하세요:")
    print("/aeo-thumbnail-generator 1 2 3 4\n")

if __name__ == "__main__":
    run_publisher()