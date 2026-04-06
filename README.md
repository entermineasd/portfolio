#AI 카드 문자 지출 분석기

카드 문자를 붙여넣으면 AI가 자동으로 분류하고 월별/카테고리별 리포트를 생성하는 웹 서비스

사용 기술
- Python, Flask
- SQLite (Flask-SQLAlchemy)
- OpenAI API (gpt-4o-mini)
- HTML/CSS

주요 기능
- 회원가입 / 로그인 / 로그아웃
- 카드 문자 AI 자동 분류 (카테고리, 가게, 금액, 날짜)
- 유저별 지출 내역 DB 저장
- 월별 / 카테고리별 리포트 생성

실행 방법
1. 필요한 라이브러리 설치
pip install flask flask-sqlalchemy openai werkzeug

2. OpenAI API 키 환경변수 설정
export OPENAI_API_KEY="your-api-key"

3. 실행
python3 final_app.py

4. 브라우저에서 접속
http://127.0.0.1:5000

파일 구조
- final_app.py : 메인 서버 코드 (Flask)
- test_ai.py : AI API 테스트 코드