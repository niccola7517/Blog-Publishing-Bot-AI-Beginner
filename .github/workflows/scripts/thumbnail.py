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
    topic_number = 1
    topic_name = "테스트 클라우드 주제"
    file_name = f"[{today_str}] 썸네일 Topic {topic_number} - {topic_name}.png"

    # 5. Gemini API(Imagen 3)를 활용한 썸네일 생성 프롬프트 구성 (스킬 룰 엄격 적용)
    client = genai.Client(api_key=api_key)
    
    # 스킬 화면에 명시된 레이아웃 및 인포그래픽 규칙을 프롬프트로 번역
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

    print("🎨 이미지 생성 중 (Imagen API 호출)...")
    try:
        # Google Imagen 3 모델 호출 (해당 API 키에 권한이 있어야 함)
        result = client.models.generate_images(
            model='imagen-3.0-generate-001',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio="16:9"
            )
        )
        
        generated_image_bytes = result.generated_images[0].image.image_bytes
        print("✅ 썸네일 이미지 생성 완료.")

    except Exception as e:
        print(f"❌ 이미지 생성 중 오류 발생: {e}")
        sys.exit(1)

    # 6. 생성된 이미지를 Google Drive로 직접 업로드
    media = MediaIoBaseUpload(io.BytesIO(generated_image_bytes), mimetype='image/png', resumable=True)
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    
    print("☁️ Google Drive에 업로드 중...")
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    # 7. 출력 규칙 (Output & Verification) 준수
    file_link = uploaded_file.get('webViewLink')
    print("\n==========================================")
    print("🎉 AEO 썸네일 생성 및 업로드 성공")
    print("==========================================")
    print(f"✅ 파일명: {file_name}")
    print(f"📁 저장 위치: {folder_name}")
    print(f"🔗 이미지 확인 링크: {file_link}")
    print("==========================================\n")

if __name__ == "__main__":
    run_thumbnail_generator()