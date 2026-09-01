import os
import io
import sys
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google import genai
from google.genai import types

def run_thumbnail_generator():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"--- [AEO Thumbnail Generator] 파이프라인 시작 ({today_str}) ---")
    
    # 1. 환경 변수 확인
    api_key = os.environ.get("AI_API_KEY")
    service_account_json = os.environ.get("GCP_SA_KEY")
    
    if not api_key:
        print("❌ AI_API_KEY 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)
    if not service_account_json:
        print("❌ GCP_SA_KEY 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)

    # 2. Google Drive API 인증 설정
    scopes = ["https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(
        eval(service_account_json), scopes=scopes
    )
    drive_service = build('drive', 'v3', credentials=credentials)

    # 3. 대상 폴더 ('Cloud-AI 포스팅 아카이브') 확인 및 폴더 ID 확보
    folder_name = "Cloud-AI 포스팅 아카이브"
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    folder_results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    folders = folder_results.get('files', [])

    if not folders:
        # 폴더가 없으면 에러 처리 (퍼블리셔 단계에서 생성되었어야 함)
        print(f"❌ '{folder_name}' 폴더를 찾을 수 없습니다.")
        sys.exit(1)
    folder_id = folders[0]['id']

    # 4. 이전 단계에서 처리된 토픽 정보 (예시 데이터 - 실제 환경에서는 json 파일 등에서 로드)
    target_keyword = "테스트 클라우드 키워드"
    topics = [
        f"{target_keyword} - [개념 이해]: 직관적인 일상 비유로 풀어낸 기술의 본질과 등장 배경",
        f"{target_keyword} - [실무 활용]: 비개발자 직장인이 업무/일상에서 바로 써먹는 생산성 향상 사례",
        f"{target_keyword} - [입문 튜토리얼]: 웹 브라우저 기반 무료 도구로 10분 만에 끝내는 0 to 1 실습 가이드",
        f"{target_keyword} - [트러블슈팅 & 꿀팁]: 에러 발생 시 대화 요령, 초보자 주의사항 및 보안 수칙"
    ]

    client = genai.Client(api_key=api_key)
    generated_links = []

    print("\n==========================================")
    print("🎨 AEO 썸네일 생성 파이프라인 시작 (4개 토픽)")
    print("==========================================")

    for i, topic_name in enumerate(topics, 1):
        file_name = f"[{today_str}] 썸네일 Topic {i} - {topic_name}.png"
        
        # 5. Gemini API(Imagen 3)를 활용한 썸네일 생성 프롬프트 구성 (스킬 룰 엄격 적용)
        prompt = f"""
        Create a highly professional, 16:9 (1920x1080) high-resolution tech blog thumbnail image.
        Topic: {topic_name}
        
        [Layout & Typography Hierarchy]
        - Background: Dark navy with a modern, technical feel.
        - Header: Top left has a blue pill badge with white text 'AI Tech'. Large, bold, crisp title. Subtitle in English. Right pill badge with 2 hashtags.
        - 2x2 Grid Layout: 4 spacious rounded-corner cards with subtle colorful top borders (Blue, Green, Yellow, Magenta).
        - Grid Content Rules: Left 65% contains text using '▣' for main titles and '•' for detailed bullets. Right 35% contains a rich, multi-layered vector infographic (NO flat icons).
        - Text Wrapping: Ensure all text inside the boxes, especially within the infographics, is strictly word-wrapped and does not overflow.
        - Infographics Rules: Use concrete real-world objects and UI mockups (e.g., stamping machine, data node tree, UI workflow, secure masking shield). DO NOT use bullet points inside the right-side graphics.
        - Bottom Banners: Include '[핵심 요약]' and '[Core FAQ]' labels at the bottom with generous padding to prevent text cut-off.
        
        Please generate an image that perfectly follows this specific UI layout for an AEO-optimized non-developer tech blog.
        """

        print(f"\n[{i}/4] 🎨 이미지 생성 중 (Topic {i})...")
        # Google Gemini 최신 모델(3.7)을 사용한 이미지 생성 (generate_content 메서드 활용)
        try:
            result = client.models.generate_content(
                model='gemini-3.7-flash',
                contents=prompt
            )
            
            # generate_content 응답에서 이미지 바이트 추출 (SDK 버전에 따라 파트 구조 접근)
            generated_image_bytes = result.candidates[0].content.parts[0].inline_data.data
            print("✅ 썸네일 이미지 생성 완료. ☁️ Drive 업로드 중...")

            # 6. 생성된 이미지를 Google Drive로 직접 업로드
            media = MediaIoBaseUpload(io.BytesIO(generated_image_bytes), mimetype='image/png', resumable=True)
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            
            uploaded_file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            file_link = uploaded_file.get('webViewLink')
            generated_links.append((file_name, file_link))
            
        except Exception as e:
            print(f"❌ Topic {i} 이미지 생성/업로드 중 오류 발생: {e}")
            sys.exit(1)

    # 7. 출력 규칙 (Output & Verification) 준수
    print("\n==========================================")
    print("🎉 AEO 썸네일 생성 및 업로드 성공 (총 4건)")
    print("==========================================")
    print(f"📁 저장 위치: {folder_name}\n")
    for file_name, file_link in generated_links:
        print(f"✅ 파일명: {file_name}")
        print(f"🔗 링크: {file_link}\n")
    print("==========================================\n")

if __name__ == "__main__":
    run_thumbnail_generator()