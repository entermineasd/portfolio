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

STYLE = """
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa; color: #333; }
    .navbar { background: #1a1a2e; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; }
    .navbar h1 { color: white; font-size: 18px; }
    .navbar a { color: #aaa; text-decoration: none; font-size: 14px; }
    .navbar a:hover { color: white; }
    .container { max-width: 750px; margin: 40px auto; padding: 0 20px; }
    .card { background: white; border-radius: 12px; padding: 30px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); }
    .card h2 { font-size: 18px; margin-bottom: 15px; color: #1a1a2e; }
    textarea { width: 100%; height: 130px; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; resize: vertical; outline: none; }
    textarea:focus { border-color: #4f46e5; }
    .btn { display: inline-block; padding: 11px 28px; background: #4f46e5; color: white; border: none; border-radius: 8px; font-size: 15px; cursor: pointer; margin-top: 12px; }
    .btn:hover { background: #4338ca; }
    .btn-red { background: #ef4444; }
    .btn-red:hover { background: #dc2626; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }
    th { background: #f1f5f9; padding: 10px 12px; text-align: left; font-weight: 600; color: #555; }
    td { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; }
    tr:hover td { background: #fafafa; }
    .total { font-size: 20px; font-weight: 700; color: #1a1a2e; margin: 20px 0 10px; }
    .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; background: #ede9fe; color: #4f46e5; }
    .loading { color: #888; font-size: 14px; margin-top: 15px; }
    input { width: 100%; padding: 11px 14px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; margin-bottom: 12px; outline: none; }
    input:focus { border-color: #4f46e5; }
    .auth-box { max-width: 400px; margin: 80px auto; }
    .error { color: #ef4444; font-size: 13px; margin-top: 8px; }
    .link { color: #4f46e5; text-decoration: none; font-size: 13px; }
    .ratio-bar { height: 6px; background: #ede9fe; border-radius: 3px; margin-top: 4px; }
    .ratio-fill { height: 6px; background: #4f46e5; border-radius: 3px; }
</style>
"""

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    expenses = Expense.query.filter_by(username=session['username']).order_by(Expense.month.desc()).all()
    history_html = ""
    if expenses:
        history_html = "<table><tr><th>월</th><th>가게</th><th>카테고리</th><th>금액</th></tr>"
        for e in expenses:
            history_html += f"<tr><td>{e.month}</td><td>{e.store}</td><td><span class='badge'>{e.category}</span></td><td>{e.amount:,}원</td></tr>"
        history_html += "</table>"
    else:
        history_html = "<p style='color:#aaa;font-size:14px;'>아직 저장된 내역이 없어요.</p>"

    return render_template_string(f"""
    <!DOCTYPE html><html lang='ko'><head><meta charset='UTF-8'><title>지출 분석기</title>{STYLE}</head>
    <body>
    <div class='navbar'>
        <h1>💳 지출 분석기</h1>
        <span style='color:#aaa;font-size:14px;'>👋 {session['username']}님 &nbsp;|&nbsp; <a href='/logout'>로그아웃</a></span>
    </div>
    <div class='container'>
        <div class='card'>
            <h2>📋 카드 문자 분석</h2>
            <p style='font-size:13px;color:#888;margin-bottom:12px;'>카드 문자를 한 줄씩 붙여넣고 분석 버튼을 눌러요.</p>
            <textarea id='input' placeholder='[Web발신] 신한카드 승인 35,000원 스타벅스 2026-03-24'></textarea>
            <button class='btn' onclick='analyze()'>📊 분석하기</button>
            <div id='result'></div>
        </div>
        <div class='card'>
            <h2>📁 저장된 내역</h2>
            {history_html}
        </div>
    </div>
    <script>
        async function analyze() {{
            const text = document.getElementById('input').value;
            document.getElementById('result').innerHTML = '<p class="loading">분석 중...</p>';
            const res = await fetch('/analyze', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{text: text}})
            }});
            const data = await res.json();
            let html = '<br><h2>📊 분석 결과</h2><table><tr><th>월</th><th>가게</th><th>카테고리</th><th>금액</th></tr>';
            data.items.forEach(item => {{
                html += `<tr><td>${{item.month}}</td><td>${{item.store}}</td><td><span class='badge'>${{item.category}}</span></td><td>${{item.amount.toLocaleString()}}원</td></tr>`;
            }});
            html += '</table>';
            html += `<div class='total'>💳 총 지출: ${{data.total.toLocaleString()}}원</div>`;
            html += '<h2 style="margin-bottom:10px;">📂 카테고리별</h2>';
            data.categories.forEach(cat => {{
                html += `<div style='margin-bottom:12px;'><div style='display:flex;justify-content:space-between;font-size:14px;'><span><span class='badge'>${{cat.name}}</span></span><span style='color:#555;'>${{cat.amount.toLocaleString()}}원 (${{cat.ratio}}%)</span></div><div class='ratio-bar'><div class='ratio-fill' style='width:${{cat.ratio}}%'></div></div></div>`;
            }});
            html += '<p style="color:green;font-size:13px;margin-top:15px;">✅ DB에 저장됐어요! 새로고침하면 저장된 내역에서 확인할 수 있어요.</p>';
            document.getElementById('result').innerHTML = html;
        }}
    </script>
    </body></html>
    """)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'username' not in session:
        return jsonify({{"error": "로그인 필요"}}), 401
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
    return render_template_string(f"""
    <!DOCTYPE html><html lang='ko'><head><meta charset='UTF-8'><title>회원가입</title>{STYLE}</head>
    <body>
    <div class='container auth-box'>
        <div class='card'>
            <h2 style='margin-bottom:20px;'>📝 회원가입</h2>
            <form method='POST'>
                <input name='username' placeholder='아이디' required>
                <input name='password' type='password' placeholder='비밀번호' required>
                <button type='submit' class='btn' style='width:100%;'>가입하기</button>
            </form>
            <p style='margin-top:15px;text-align:center;'>이미 계정이 있나요? <a href='/login' class='link'>로그인</a></p>
            <div class='error'>{error}</div>
        </div>
    </div>
    </body></html>
    """)

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
    return render_template_string(f"""
    <!DOCTYPE html><html lang='ko'><head><meta charset='UTF-8'><title>로그인</title>{STYLE}</head>
    <body>
    <div class='container auth-box'>
        <div class='card'>
            <h2 style='margin-bottom:20px;'>🔐 로그인</h2>
            <form method='POST'>
                <input name='username' placeholder='아이디' required>
                <input name='password' type='password' placeholder='비밀번호' required>
                <button type='submit' class='btn' style='width:100%;'>로그인</button>
            </form>
            <p style='margin-top:15px;text-align:center;'>계정이 없나요? <a href='/register' class='link'>회원가입</a></p>
            <div class='error'>{error}</div>
        </div>
    </div>
    </body></html>
    """)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)