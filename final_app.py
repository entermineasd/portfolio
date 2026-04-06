from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI
import os
import json
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "supersecretkey123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///final.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    month = db.Column(db.String(10), nullable=False)
    store = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Integer, nullable=False)

with app.app_context():
    db.create_all()

HTML_BASE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: sans-serif; max-width: 700px; margin: 50px auto; padding: 20px; }}
        input, textarea {{ width: 100%; padding: 10px; margin: 8px 0; box-sizing: border-box; font-size: 14px; }}
        textarea {{ height: 150px; }}
        button {{ padding: 10px 30px; background: #4CAF50; color: white; border: none; font-size: 16px; cursor: pointer; border-radius: 5px; margin-top: 10px; }}
        button:hover {{ background: #45a049; }}
        a {{ color: #4CAF50; }}
        .error {{ color: red; margin-top: 10px; }}
        .box {{ border: 1px solid #ddd; padding: 30px; border-radius: 10px; max-width: 400px; margin: 100px auto; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f2f2f2; }}
        .total {{ font-size: 18px; font-weight: bold; margin: 20px 0; }}
        nav {{ margin-bottom: 20px; }}
    </style>
</head>
<body>
    {content}
</body>
</html>
"""

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    expenses = Expense.query.filter_by(username=session['username']).all()
    history_html = ""
    if expenses:
        history_html = "<h3>📁 저장된 내역</h3><table><tr><th>월</th><th>가게</th><th>카테고리</th><th>금액</th></tr>"
        for e in expenses:
            history_html += f"<tr><td>{e.month}</td><td>{e.store}</td><td>{e.category}</td><td>{e.amount:,}원</td></tr>"
        history_html += "</table>"

    return render_template_string(HTML_BASE.format(
        title="지출 분석기",
        content=f"""
            <nav>👋 <b>{session['username']}</b>님 | <a href="/logout">로그아웃</a></nav>
            <h2>💳 카드 문자 지출 분석기</h2>
            <p>카드 문자를 한 줄씩 붙여넣고 분석 버튼을 눌러요.</p>
            <textarea id="input" placeholder="[Web발신] 신한카드 승인 35,000원 스타벅스 2026-03-24"></textarea>
            <br>
            <button onclick="analyze()">📊 분석하기</button>
            <div id="result"></div>
            {history_html}
            <script>
                async function analyze() {{
                    const text = document.getElementById('input').value;
                    document.getElementById('result').innerHTML = '<p>분석 중...</p>';
                    const res = await fetch('/analyze', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{text: text}})
                    }});
                    const data = await res.json();
                    let html = '<h3>📋 분석 결과</h3><table><tr><th>월</th><th>가게</th><th>카테고리</th><th>금액</th></tr>';
                    data.items.forEach(item => {{
                        html += `<tr><td>${{item.month}}</td><td>${{item.store}}</td><td>${{item.category}}</td><td>${{item.amount.toLocaleString()}}원</td></tr>`;
                    }});
                    html += '</table>';
                    html += `<div class="total">💳 총 지출: ${{data.total.toLocaleString()}}원</div>`;
                    html += '<h3>📂 카테고리별</h3><table><tr><th>카테고리</th><th>금액</th><th>비율</th></tr>';
                    data.categories.forEach(cat => {{
                        html += `<tr><td>${{cat.name}}</td><td>${{cat.amount.toLocaleString()}}원</td><td>${{cat.ratio}}%</td></tr>`;
                    }});
                    html += '</table>';
                    html += '<p style="color:green;">✅ DB에 저장됐어요! 새로고침하면 저장된 내역에서 확인할 수 있어요.</p>';
                    document.getElementById('result').innerHTML = html;
                }}
            </script>
        """
    ))

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'username' not in session:
        return jsonify({"error": "로그인 필요"}), 401
    lines = request.json['text'].strip().split('\n')
    items = []
    카테고리별 = defaultdict(int)
    총합 = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": '너는 카드 문자 분석 도구야. 반드시 JSON만 출력해. 다른 텍스트 절대 금지. category는 반드시 음식, 편의점, 쇼핑, 미용, 교통, 의료, 문화, 기타 중 하나만 써. 형식: {"category": "카테고리", "store": "가게", "amount": 숫자, "month": "YYYY-MM"}'},
                    {"role": "user", "content": line}
                ],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            items.append(data)
            db.session.add(Expense(
                username=session['username'],
                month=data['month'],
                store=data['store'],
                category=data['category'],
                amount=data['amount']
            ))
            db.session.commit()
            카테고리별[data['category']] += data['amount']
            총합 += data['amount']
        except:
            continue
    categories = [
        {"name": cat, "amount": amt, "ratio": round(amt / 총합 * 100, 1)}
        for cat, amt in sorted(카테고리별.items(), key=lambda x: x[1], reverse=True)
    ]
    return jsonify({"items": items, "total": 총합, "categories": categories})

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            error = "이미 존재하는 아이디예요."
        else:
            db.session.add(User(username=username, password=generate_password_hash(password)))
            db.session.commit()
            return redirect(url_for('login'))
    return render_template_string(HTML_BASE.format(
        title="회원가입",
        content=f"""
            <div class="box">
                <h2>📝 회원가입</h2>
                <form method="POST">
                    <input name="username" placeholder="아이디" required>
                    <input name="password" type="password" placeholder="비밀번호" required>
                    <button type="submit">가입하기</button>
                </form>
                <p style="margin-top:15px;">이미 계정이 있나요? <a href="/login">로그인</a></p>
                <div class="error">{error}</div>
            </div>
        """
    ))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            error = "아이디 또는 비밀번호가 틀렸어요."
    return render_template_string(HTML_BASE.format(
        title="로그인",
        content=f"""
            <div class="box">
                <h2>🔐 로그인</h2>
                <form method="POST">
                    <input name="username" placeholder="아이디" required>
                    <input name="password" type="password" placeholder="비밀번호" required>
                    <button type="submit">로그인</button>
                </form>
                <p style="margin-top:15px;">계정이 없나요? <a href="/register">회원가입</a></p>
                <div class="error">{error}</div>
            </div>
        """
    ))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)