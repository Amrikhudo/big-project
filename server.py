#    ╔═══════════════════════════════════════╗
#    ║                                       ║
#    ║        ▲     ▲     ▲     ▲            ║
#    ║       / \   / \   / \   / \           ║
#    ║      / A \ / M \ / R \ / I \          ║
#    ║     /_____/_____/_____/_____\         ║
#    ║                                       ║
#    ║         Code with meaning.            ║
#    ║                                       ║
#    ║                                       ║
#    ║           by: Amrikhudo               ║
#    ╚═══════════════════════════════════════╝


from flask import Flask, request, session, render_template, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import re
import os
import uuid

app = Flask(__name__, template_folder='template')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'secret_key'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

messages = []
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_unique_filename(filename):
    _, ext = os.path.splitext(filename)
    return f"{uuid.uuid4().hex}{ext}"

questions_and_answers = {
    r'привет|здравствуй|hello|hi': 'Здравствуйте! Чем я могу Вам помочь?',
    r'как дела|как жизнь': 'Спасибо, у меня все хорошо! Готов помочь вам с любыми вопросами о нашем сервисе.',
    r'что ты умеешь': 'Я могу отвечать на различные вопросы, касающиеся нашего сайта и услуг. Я помогу с информацией о находках и пропажах, процессе размещения объявлений, и как связаться с владельцами находок или теми, кто что-то потерял.',
    r'где вы находитесь|ваш адрес': 'К сожалению, у нас нет физического офиса. Мы онлайн-сервис и работаем исключительно через интернет.',
    r'время работы|график работы': 'Наш сайт и служба поддержки работают круглосуточно, без выходных.',
    r'гарантия|гарантия безопасности': 'По поводу гарантии безопасности вы можете подробно посмотреть в разделе "Гарантия безопасности"',
    r'помощь|инструкция': 'По поводу гарантии безопасности вы можете подробно посмотреть в разделе "Инструкция"',
    r'контакты|как связаться|телефон|email': 'Вы можете связаться с нами по электронной почте example@mail.com или по телефону +7 (800) 555-35-35. Также можно воспользоваться формой обратной связи на сайте.',
    r'как зарегистрироваться|регистрация': 'Для регистрации нажмите кнопку "Регистрация" в верхнем меню сайта. Заполните необходимые поля: имя пользователя, электронную почту и пароль. После этого вы сможете размещать объявления и комментировать.',
    r'как войти в аккаунт|войти|вход': 'Нажмите кнопку "Войти" в верхнем меню сайта. Введите свой логин и пароль для входа в систему.',
    r'что делать если(.*?)нашел|как вернуть найденную вещь': 'Если вы нашли чужую вещь, напишите про находку в службу поддержки. Укажите место и время находки, опишите предмет. Дождитесь отклика поддержки.',
    r'что делать если(.*?)потерял|как найти потерянную вещь': 'Если вы потеряли вещь, напишите про пропажу в службу поддержки. Укажите место и время, когда предположительно была утеряна вещь, подробно опишите её и по возможности прикрепите фотографию. Регулярно проверяйте раздел "Находки".',
    r'.*': 'Извините, я не совсем понимаю ваш вопрос. Попробуйте переформулировать или задать другой вопрос о нашем сервисе. Я могу рассказать о размещении объявлений, поиске вещей или процедуре возврата находок.'
}


new_questions_and_answers = {}
for pattern, answer in questions_and_answers.items():
    if pattern != r'.*':
        new_questions_and_answers[pattern] = answer

questions_and_answers = new_questions_and_answers

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_super_admin = db.Column(db.Boolean, default=False)
    reviews = db.relationship('Review', backref='user', lazy='dynamic')

class UnansweredQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_question = db.Column(db.Text, nullable=False)
    admin_answer = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  
    user = db.relationship('User', backref='questions', lazy='joined') 
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    answered = db.Column(db.Boolean, default=False)
    user_seen = db.Column(db.Boolean, default=False)
    user_session = db.Column(db.String(100), nullable=True)  


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product = db.Column(db.String(80), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    replies = db.relationship('Review', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    images = db.relationship('ReviewImage', backref='review', lazy='dynamic')
    pinned = db.Column(db.Boolean, default=False)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user_session = db.Column(db.String(100), nullable=True)
    sender_type = db.Column(db.String(10), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

class ReviewImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    filename = db.Column(db.String(100))
    mimetype = db.Column(db.String(100))

with app.app_context():
    db.create_all()


def get_authenticated_user():
    if 'token' not in session:
        return None
    
    try:
        data = jwt.decode(session['token'], app.config['SECRET_KEY'], algorithms=['HS256'])
        return User.query.get(data['user_id'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        session.pop('token', None)
        return None

@app.route('/api/products', methods=['GET'])
def get_products():
    products = [
        {'id': 1, 'name': 'Пропала кошка', 'price': 699},
        {'id': 2, 'name': 'Пропал велосипед', 'price': 649},
        {'id': 3, 'name': 'Нашла золотое кольцо', 'price': 499},
        {'id': 4, 'name': 'Пропал кошелек с деньгами', 'price': 499},
        {'id': 5, 'name': 'Нашёл зонтик', 'price': 649},
        {'id': 6, 'name': 'Нашёл ноутбук Dell', 'price': 699},
    ]
    return jsonify(products)

@app.route('/api/cart', methods=['GET'])
def get_cart():
    user = get_authenticated_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    cart = user.cart
    if cart is None:
        return jsonify([])
        
    cart_items = [{'id': item.id, 'name': item.currency, 'price': item.price, 'quantity': item.quantity} 
                  for item in cart.items]
    return jsonify(cart_items)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    data = request.form
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return render_template('register.html', error='Пожалуйста, заполните все поля.', error_color='red')

    if User.query.filter_by(username=username).first():
        return render_template('register.html', error='Это имя пользователя уже занято. Пожалуйста, выберите другое.',
                               error_color='red')

    if User.query.filter_by(email=email).first():
        return render_template('register.html',
                               error='Этот адрес электронной почты уже зарегистрирован. Пожалуйста, используйте другой адрес.',
                               error_color='red')

    if len(password) < 8 or not any(char.isdigit() for char in password) or not any(
            char.isupper() for char in password):
        return render_template('register.html',
                               error='Пароль должен содержать не менее 8 символов, включая хотя бы одну цифру и одну заглавную букву.',
                               error_color='red')

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(username=username, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()


    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    data = request.form
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password, password):
        return render_template('login.html',
                               error='Неверное имя пользователя или пароль. Пожалуйста, попробуйте снова.',
                               error_color='red')

    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }, app.config['SECRET_KEY'])

    session['token'] = token
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('token', None)
    return redirect(url_for('index'))

@app.route('/add_review/<product>', methods=['POST'])
def add_review(product):
    user = get_authenticated_user()
    if not user:
        return redirect(url_for('login'))

    comment = request.form.get('comment')
    if not comment:
        return 'Отсутствуют обязательные поля', 400

    review = Review(user_id=user.id, product=product, comment=comment)
    db.session.add(review)
    db.session.commit()

    images = request.files.getlist('images')
    for image in images:
        if image.filename:
            filename = get_unique_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)

            review_image = ReviewImage(review_id=review.id, filename=filename, mimetype=image.mimetype)
            db.session.add(review_image)

    db.session.commit()

    return redirect(url_for(f'index{product_routes.get(product, 3)}'))

@app.route('/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    user = get_authenticated_user()
    if not user:
        return redirect(url_for('login'))

    review = Review.query.get(review_id)
    if not review or (review.user_id != user.id and not user.is_admin):
        return 'Вы не можете удалить этот отзыв', 403

    product = review.product
    db.session.delete(review)
    db.session.commit()

    return redirect(url_for(f'index{product_routes.get(product, 3)}'))

@app.route('/create_admin', methods=['GET'])
def create_admin():
    admin = User.query.filter_by(username='Amrikhudo').first()
    if admin:
        return "Admin account already exists"
    
    hashed_password = generate_password_hash('Admin123', method='pbkdf2:sha256')
    admin = User(username='Amrikhudo', email='admin@example.com', password=hashed_password, is_admin=True)
    db.session.add(admin)
    db.session.commit()
    
    
    return "Admin account created successfully"

@app.route('/add_reply/<int:review_id>', methods=['POST'])
def add_reply(review_id):
    user = get_authenticated_user()
    if not user:
        return redirect(url_for('login'))

    comment = request.form.get('reply_comment')
    parent_review = Review.query.get(review_id)
    
    if not comment or not parent_review:
        return 'Отсутствуют обязательные поля', 400
    
    reply = Review(
        user_id=user.id, 
        product=parent_review.product, 
        comment=comment,
        parent_id=review_id
    )
    
    db.session.add(reply)
    db.session.commit()
    
    return redirect(url_for(f'index{product_routes.get(parent_review.product, 3)}'))

@app.route('/toggle_pin_review/<int:review_id>', methods=['POST'])
def toggle_pin_review(review_id):
    user = get_authenticated_user()
    if not user or not user.is_admin:
        return redirect(url_for('login'))

    review = Review.query.get_or_404(review_id)
    
    if review.parent_id is not None:
        return redirect(url_for(f'index{product_routes.get(review.product, 3)}'))
    
    review.pinned = not review.pinned
    
    if review.pinned:
        other_pinned = Review.query.filter(
            Review.product == review.product,
            Review.id != review.id,
            Review.pinned == True
        ).all()
        for other in other_pinned:
            other.pinned = False
    
    db.session.commit()
    
    return redirect(url_for(f'index{product_routes.get(review.product, 3)}'))

@app.route('/admin/answer_question/<int:question_id>', methods=['POST'])
def answer_question(question_id):
    user = get_authenticated_user()
    if not user or not user.is_admin:
        return redirect(url_for('index'))
    
    question = UnansweredQuestion.query.get_or_404(question_id)
    admin_answer = request.form.get('admin_answer')
    
    if admin_answer:
        question.admin_answer = admin_answer
        question.answered = True
        db.session.commit()
        
        if question.user_question not in questions_and_answers:
            questions_and_answers[question.user_question] = admin_answer
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_admin/<int:user_id>', methods=['POST'])
def toggle_admin(user_id):
    current_user = get_authenticated_user()
    if not current_user or not current_user.is_admin:
        return redirect(url_for('index'))
    
    user_to_update = User.query.get_or_404(user_id)
    
    if user_to_update.is_super_admin:
        return redirect(url_for('admin_dashboard'))
    
    if not current_user.is_super_admin and user_to_update.is_admin:
        return redirect(url_for('admin_dashboard'))
    

    user_to_update.is_admin = not user_to_update.is_admin
    db.session.commit()
    
    return redirect(url_for('admin_dashboard'))


@app.route('/send_message', methods=['POST'])
def send_message():
    message = request.form['message']
    user = get_authenticated_user()
    user_id = user.id if user else None
    
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    user_session = session['session_id']
    
    user_chat_message = ChatMessage(
        user_id=user_id,
        user_session=user_session,
        sender_type='user',
        message=message
    )
    db.session.add(user_chat_message)

    exact_match = UnansweredQuestion.query.filter_by(
        user_question=message, 
        answered=True
    ).first()
    
    if exact_match and exact_match.admin_answer:
        bot_response = exact_match.admin_answer
        found_answer = True
    else:
        found_answer = False
        for question_pattern, answer in questions_and_answers.items():
            if question_pattern != r'.*' and re.search(question_pattern, message, re.IGNORECASE):
                bot_response = answer
                found_answer = True
                break

        if not found_answer:
            bot_response = "Извините, я не смог распознать ваш запрос. Наш администратор рассмотрит ваш вопрос и ответит на него в ближайшее время."
            
            new_question = UnansweredQuestion(
                user_question=message, 
                user_id=user_id,
                user_session=user_session,
                answered=False,
                user_seen=False
            )
            db.session.add(new_question)
    
    bot_chat_message = ChatMessage(
        user_id=user_id,
        user_session=user_session,
        sender_type='bot',
        message=bot_response
    )
    db.session.add(bot_chat_message)
    db.session.commit()
   
    history = get_chat_history(user_id, user_session)
    
    return jsonify({'success': True, 'messages': history})

@app.route('/get_chat_history', methods=['GET'])
def retrieve_chat_history():
    user = get_authenticated_user()
    user_id = user.id if user else None
    user_session = session.get('session_id')
    
    history = get_chat_history(user_id, user_session)
    return jsonify({'success': True, 'messages': history})

def get_chat_history(user_id=None, user_session=None):
    query = ChatMessage.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    elif user_session:
        query = query.filter_by(user_session=user_session)
    else:
        return []
    
    messages = query.order_by(ChatMessage.timestamp).all()
    return [(msg.sender_type, msg.message) for msg in messages]

@app.route('/check_admin_answers', methods=['GET'])
def check_admin_answers():
    user_session = session.get('session_id')
    user = get_authenticated_user()
    user_id = user.id if user else None
    
    if not user_session and not user_id:
        return jsonify({'has_new_answers': False})
    

    query = UnansweredQuestion.query.filter_by(answered=True)
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    elif user_session:
        query = query.filter_by(user_session=user_session)
    
    
    unanswered = query.filter_by(user_seen=False).all()
    
    if unanswered:
        answers = []
        for question in unanswered:
            answers.append({
                'question': question.user_question,
                'answer': question.admin_answer
            })
            
            question.user_seen = True
        
        db.session.commit()
        return jsonify({'has_new_answers': True, 'answers': answers})
    
    return jsonify({'has_new_answers': False})

@app.route('/create_super_admin', methods=['GET'])
def create_super_admin():
    admin = User.query.filter_by(username='Amrikhudo').first()
    if not admin:
        hashed_password = generate_password_hash('Admin123', method='pbkdf2:sha256')
        admin = User(username='Amrikhudo', email='admin@example.com', password=hashed_password, is_admin=True, is_super_admin=True)
        db.session.add(admin)
        db.session.commit()
        
        
        return "Super Admin account created successfully"
    else:
        admin.is_super_admin = True
        db.session.commit()
        return "Account upgraded to Super Admin successfully"



@app.route('/admin/dashboard')
def admin_dashboard():
    user = get_authenticated_user()
    if not user or not user.is_admin:
        return redirect(url_for('index'))
    
    users = User.query.all()
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    unanswered_questions = UnansweredQuestion.query.filter_by(answered=False).order_by(UnansweredQuestion.created_at.desc()).all()
    answered_questions = UnansweredQuestion.query.filter_by(answered=True).order_by(UnansweredQuestion.created_at.desc()).limit(20).all()
    
    return render_template(
        'admin_dashboard.html', 
        users=users, 
        reviews=reviews, 
        user=user, 
        unanswered_questions=unanswered_questions,
        answered_questions=answered_questions
    )


@app.route('/')
def index():
    user = get_authenticated_user()
    return render_template('index.html', user=user)


@app.route('/garantiya')
def garantiya():
    user = get_authenticated_user()
    return render_template('garantiya.html', user=user)

@app.route('/help')
def help():
    user = get_authenticated_user()
    return render_template('help.html', user=user)

product_routes = {
    'Пропала кошка': 3,
    'Пропал велосипед': 4,
    'Нашла золотое кольцо': 5,
    'Пропал кошелек с деньгами': 6,
    'Нашёл зонтик': 7,
    'Нашёл ноутбук Dell': 8,
    'Золотые руки': 9
}



def get_product_reviews(product_name):
    return Review.query.filter_by(
        product=product_name, 
        parent_id=None
    ).order_by(
        Review.pinned.desc(),  
        Review.created_at.desc()  
    ).all()

@app.route('/card2')
def index3():
    user = get_authenticated_user()
    reviews = get_product_reviews('Пропала кошка')
    return render_template('index3.html', user=user, reviews=reviews)

@app.route('/card3')
def index4():
    user = get_authenticated_user()
    reviews = get_product_reviews('Пропал велосипед')
    return render_template('index4.html', user=user, reviews=reviews)

@app.route('/card4')
def index5():
    user = get_authenticated_user()
    reviews = get_product_reviews('Нашла золотое кольцо')
    return render_template('index5.html', user=user, reviews=reviews)

@app.route('/card5')
def index6():
    user = get_authenticated_user()
    reviews = get_product_reviews('Пропал кошелек с деньгами')
    return render_template('index6.html', user=user, reviews=reviews)

@app.route('/card6')
def index7():
    user = get_authenticated_user()
    reviews = get_product_reviews('Нашёл зонтик')
    return render_template('index7.html', user=user, reviews=reviews)

@app.route('/card7')
def index8():
    user = get_authenticated_user()
    reviews = get_product_reviews('Нашёл ноутбук Dell')
    return render_template('index8.html', user=user, reviews=reviews)


if __name__ == '__main__':
    app.run(debug=True)
