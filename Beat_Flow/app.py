from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # 메모리 기반 기본 데이터베이스 설정
app.config['SQLALCHEMY_BINDS'] = {
    'users': 'sqlite:///users.db',
    'songs': 'sqlite:///song.db',
    'chats': 'sqlite:///chat.db'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 사용자 모델 정의
class User(db.Model):
    __bind_key__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


class Song(db.Model):
    __bind_key__ = 'songs'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    artist = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(100), nullable=False)

class ChatMessage(db.Model):
    __bind_key__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    artist = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    username = db.Column(db.String(50), nullable=False)  # 사용자 닉네임 추가
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())




with app.app_context():
    db.create_all()  # 모든 바인드된 데이터베이스(users.db, song.db)를 생성



@app.route('/')
def home():
    #songs = Song.query.all() 
    username = session.get('username')
    return render_template('index.html', username=username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # 사용자 확인
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['username'] = username
            
            return redirect(url_for('home'))
        else:
            flash('잘못된 사용자 이름 또는 비밀번호를 입력 하셨습니다.', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        # 사용자 확인 및 암호화
        user = User.query.filter_by(username=username).first()
        if user:
            flash('사용자 이름이 이미 존재합니다.', 'error')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(email=email, username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('회원가입이 성공적으로 완료했습니다. 로그인 해주세요.', 'success')
            return redirect(url_for('login'))
    
    return render_template('signup.html')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/add_song', methods=['GET', 'POST'])
def add_song():
    if 'username' not in session:
        flash('로그인이 필요합니다.', 'error')
        return redirect(url_for('login'))

    # 현재 로그인한 사용자를 가져옴
    user = User.query.filter_by(username=session['username']).first()

    # 관리자인지 확인

    if not user.is_admin:  # 수정된 부분
        return render_template('add_song.html', admin_only=True)

    if request.method == 'POST':
        title = request.form['title']
        artist = request.form['artist']
        filename = request.form['filename']
        
        new_song = Song(title=title, artist=artist, filename=filename)
        db.session.add(new_song)
        db.session.commit()
        
        flash('노래가 정상적으로 등록되었습니다!', 'success')
        return redirect(url_for('add_song'))
    
    return render_template('add_song.html')


@app.route('/search')
def search():
    username = session.get('username')
    query = request.args.get('query', '').lower()
    results = Song.query.filter(
        (Song.title.ilike(f'%{query}%')) | 
        (Song.artist.ilike(f'%{query}%'))
    ).all()
    
    return render_template('search.html', results=results,username=username)

@app.route('/play/<int:song_id>', methods=['GET', 'POST'])
def play_song(song_id):
    username = session.get('username')
    song = Song.query.get_or_404(song_id)

    # POST 요청 시 채팅 메시지 처리
    if request.method == 'POST':
        message = request.form['message']
        username = session.get('username') # 현재 로그인된 사용자의 닉네임 가져오기
        new_message = ChatMessage(artist=song.artist, message=message, username=username)
        db.session.add(new_message)
        db.session.commit()
        return redirect(url_for('play_song', song_id=song_id)) 

    # GET요청 시 채팅 메시지
    messages = ChatMessage.query.filter_by(artist=song.artist).order_by(ChatMessage.timestamp.desc()).all()

    return render_template('play_song.html', song=song, messages=messages,username=username)



@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('로그아웃이 완료 되었습니다.', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
