from openai import OpenAI
import os
import json
import csv
from collections import defaultdict

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

messages = [
    "[Web발신] 신한카드 승인 35,000원 스타벅스 2026-03-24",
    "[Web발신] 삼성카드 승인 12,000원 GS25 2026-03-24",
    "[Web발신] 국민카드 승인 85,000원 이마트 2026-03-24",
    "[Web발신] 신한카드 승인 45,000원 올리브영 2026-03-24",
    "[Web발신] 신한카드 승인 28,000원 맥도날드 2026-03-10",
    "[Web발신] 삼성카드 승인 15,000원 다이소 2026-03-15",
    "[Web발신] 국민카드 승인 120,000원 쿠팡 2026-02-20",
    "[Web발신] 신한카드 승인 9,000원 파리바게뜨 2026-02-14",
]

결과 = []
카테고리별 = defaultdict(int)
월별 = defaultdict(int)
총합 = 0

for msg in messages:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": '너는 카드 문자 분석 도구야. 반드시 JSON만 출력해. 다른 텍스트 절대 금지. category는 반드시 음식, 편의점, 쇼핑, 미용, 교통, 의료, 문화, 기타 중 하나만 써. 형식: {"category": "카테고리", "store": "가게", "amount": 숫자, "month": "YYYY-MM"}'},
                {"role": "user", "content": msg}
            ],
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        결과.append(data)
        카테고리별[data['category']] += data['amount']
        월별[data['month']] += data['amount']
        총합 += data['amount']
    except Exception as e:
        print(f"에러: {e}")

# CSV 저장
with open(os.path.expanduser("~/Desktop/지출내역.csv"), "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["month", "store", "category", "amount"])
    writer.writeheader()
    writer.writerows(결과)

# 리포트 출력
print("=" * 35)
print("📊 지출 리포트")
print("=" * 35)

print("\n📅 월별 지출")
for month, amount in sorted(월별.items()):
    print(f"  {month}: {amount:,}원")

print(f"\n💳 총 지출: {총합:,}원")

print("\n📂 카테고리별 비율")
for cat, amount in sorted(카테고리별.items(), key=lambda x: x[1], reverse=True):
    비율 = (amount / 총합) * 100
    bar = "█" * int(비율 / 5)
    print(f"  {cat:6} {bar} {amount:,}원 ({비율:.1f}%)")

print("=" * 35)
print("\n✅ 바탕화면에 지출내역.csv 저장 완료!")