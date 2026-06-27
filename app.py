from flask import Flask, render_template, request, redirect, session, url_for
from flask_mail import Mail, Message
from datetime import datetime, timedelta, time
import random
import mysql.connector

app = Flask(__name__)
app.secret_key = "online_exam_secret"
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = 'lakshmisatya0613@gmail.com'

app.config['MAIL_PASSWORD'] = 'esln hvdo pfsb rwmg'

mail = Mail(app)
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Lalitha@2006",
    database="online_exam"
)

cursor = db.cursor(buffered=True)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return "Passwords do not match"

        otp = str(random.randint(100000, 999999))

        session['otp'] = otp
        session['name'] = name
        session['email'] = email
        session['phone'] = phone
        session['password'] = password

        msg = Message(
            'Online Exam Portal OTP',
            sender='lakshmisatya0613@gmail.com',
            recipients=[email]
        )

        msg.body = f'Your OTP is: {otp}'

        mail.send(msg)

        return redirect('/verify_otp')

    return render_template('register.html')
@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():

    if request.method == 'POST':

        entered_otp = request.form['otp']

        if entered_otp == session.get('otp'):

            sql = """
            INSERT INTO students
            (name,email,password,phone)
            VALUES(%s,%s,%s,%s)
            """

            values = (
                session['name'],
                session['email'],
                session['password'],
                session['phone']
            )

            cursor.execute(sql, values)
            db.commit()

            return render_template(
    'registration_success.html',
    name=session['name']
)

        else:
            return "Invalid OTP"

    return render_template('verify_otp.html')
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        cursor = db.cursor()

        sql = """
        SELECT * FROM students
        WHERE email=%s AND password=%s
        """

        cursor.execute(sql, (email, password))
        student = cursor.fetchone()
        if student:

            session['email'] = email

            return redirect('/dashboard')

        else:
            return render_template(
        "invalid_student_login.html"
    )
        

    return render_template('login.html')
@app.route('/admin_login', methods=['GET','POST'])
def admin_login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        sql = """
        SELECT * FROM admin
        WHERE username=%s AND password=%s
        """

        cursor.execute(sql, (username,password))

        admin = cursor.fetchone()

        if admin:
            return render_template('admin_dashboard.html')
        else:
            return render_template(
    "invalid_admin.html"
)

    return render_template('admin_login.html')
@app.route('/add_question/<int:exam_id>', methods=['GET','POST'])
def add_question(exam_id):
    cursor.execute(
        "SELECT exam_name FROM exams WHERE id=%s",
        (exam_id,)
    )
    exam=cursor.fetchone()
    

    if request.method == 'POST':

        question = request.form['question']
        option1 = request.form['option1']
        option2 = request.form['option2']
        option3 = request.form['option3']
        option4 = request.form['option4']
        correct_answer = request.form['correct_answer']

        sql = """
        INSERT INTO questions
        (question,option1,option2,option3,option4,correct_answer,exam_id)
        VALUES(%s,%s,%s,%s,%s,%s,%s)
        """

        cursor.execute(sql,(
            question,
            option1,
            option2,
            option3,
            option4,
            correct_answer,
            exam_id
        ))

        db.commit()

        session['remaining_questions'] -= 1

        if session['remaining_questions'] > 0:
        
            return redirect(
                url_for(
                    'add_question',
                    exam_id=exam_id
                )
            )

        session.pop('remaining_questions')
        session.pop('total_questions')

        return redirect(
            url_for(
                'view_questions',
                exam_id=exam_id
            )
        )

        

    return render_template("add_question.html",exam=exam)
@app.route('/exam/<int:exam_id>', methods=['GET', 'POST'])
def exam(exam_id):

    cursor.execute(
        "SELECT * FROM exams WHERE id=%s",
        (exam_id,)
    )

    exam_data = cursor.fetchone()

    exam_name = exam_data[1]
    exam_date = exam_data[2]
    start_time = exam_data[3]
    end_time = exam_data[4]

    from datetime import datetime, timedelta

    if isinstance(start_time, timedelta):
        start_time = (datetime.min + start_time).time()

    if isinstance(end_time, timedelta):
        end_time = (datetime.min + end_time).time()

    today = datetime.now().date()
    current_time = datetime.now().time()

    if today != exam_date:

        return render_template(
            "exam_not_available.html",
            message="Exam is not available today."
        )

    if current_time < start_time:

        return render_template(
            "exam_not_available.html",
            message="Exam has not started yet."
        )

    if current_time > end_time:

        return render_template(
            "exam_not_available.html",
            message="Exam time is over."
        )

    cursor.execute(
        "SELECT * FROM questions WHERE exam_id=%s",
        (exam_id,)
    )

    questions = cursor.fetchall()

    # Official exam timings
    exam_start_time = datetime.combine(today, start_time)
    exam_end_time = datetime.combine(today, end_time)

    # Remaining time
    remaining_seconds = int(
        (exam_end_time - datetime.now()).total_seconds()
    )

    if remaining_seconds <= 0:

        return render_template(
            "exam_not_available.html",
            message="Your exam time is over."
        )

    if request.method == 'POST':

        score = 0

        for q in questions:

            question_id = q[0]
            correct_answer = q[6]

            student_answer = request.form.get(
                f"q{question_id}"
            )

            if student_answer == correct_answer:
                score += 1

        email = session.get("email")

        cursor.execute("""
            INSERT INTO results
            (student_email, exam_name, score)
            VALUES(%s,%s,%s)
        """,
        (
            email,
            exam_name,
            score
        ))

        db.commit()

        return render_template(
            "result.html",
            score=score
        )

    return render_template(
        "exam.html",
        questions=questions,
        exam_name=exam_name,
        remaining_seconds=remaining_seconds
    )
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
@app.route('/my_results')
def my_results():

    email = session.get('email')

    cursor.execute(
        """
        SELECT *
        FROM results
        WHERE student_email=%s
        """,
        (email,)
    )

    results = cursor.fetchall()

    return render_template(
        'my_results.html',
        results=results
    )
@app.route('/all_results')
def all_results():

    cursor.execute("SELECT * FROM results")

    results = cursor.fetchall()

    return render_template(
        'all_results.html',
        results=results
    )
@app.route('/view_questions/<int:exam_id>')
def view_questions(exam_id):


    # Get exam name
    cursor.execute(
        "SELECT exam_name FROM exams WHERE id=%s",
        (exam_id,)
    )

    exam = cursor.fetchone()

    # Get questions of that exam
    cursor.execute(
        """
        SELECT *
        FROM questions
        WHERE exam_id=%s
        """,
        (exam_id,)
    )

    questions = cursor.fetchall()

    return render_template(
        "view_questions.html",
        exam=exam,
        exam_id=exam_id,
        questions=questions
        
        
    )
@app.route('/delete_question/<int:id>')
def delete_question(id):

    # Get exam_id before deleting
    cursor.execute(
        "SELECT exam_id FROM questions WHERE id=%s",
        (id,)
    )

    question = cursor.fetchone()

    if not question:
        return "Question Not Found"

    exam_id = question[0]

    # Delete the question
    cursor.execute(
        "DELETE FROM questions WHERE id=%s",
        (id,)
    )

    db.commit()

    # Return to the same exam's questions
    return redirect(
        url_for(
            'view_questions',
            exam_id=exam_id
        )
    )
@app.route('/edit_question/<int:id>', methods=['GET','POST'])
def edit_question(id):
    cursor.execute(
        "SELECT * FROM questions WHERE id=%s",
        (id,)
    )

    question = cursor.fetchone()

    if not question:
        return "Question Not Found"

    exam_id = question[7]

    if request.method == 'POST':

        question = request.form['question']
        option1 = request.form['option1']
        option2 = request.form['option2']
        option3 = request.form['option3']
        option4 = request.form['option4']
        correct_answer = request.form['correct_answer']

        sql = """
        UPDATE questions
        SET question=%s,
            option1=%s,
            option2=%s,
            option3=%s,
            option4=%s,
            correct_answer=%s
        WHERE id=%s
        """

        cursor.execute(sql, (
            question,
            option1,
            option2,
            option3,
            option4,
            correct_answer,
            id
        ))

        db.commit()

        return redirect(
    url_for(
        'view_questions',
        exam_id=exam_id
    )
)

   

    return render_template(
        'edit_question.html',
        question=question
    )
@app.route('/add_exam', methods=['GET', 'POST'])
def add_exam():

    if request.method == 'POST':

        exam_name = request.form['exam_name']
        exam_date = request.form['exam_date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        status = request.form['status']

        sql = """
        INSERT INTO exams
        (exam_name, exam_date, start_time, end_time, status)
        VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(sql, (
            exam_name,
            exam_date,
            start_time,
            end_time,
            status
        ))

        db.commit()
        exam_id=cursor.lastrowid

        

        return redirect(
    url_for(
        'question_count',
        exam_id=exam_id
    )
)

    return render_template('add_exam.html')
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():

    if request.method == 'POST':

        email = request.form['email']

        cursor.execute(
            "SELECT * FROM students WHERE email=%s",
            (email,)
        )

        student = cursor.fetchone()

        if student:

            otp = str(random.randint(100000, 999999))

            session['reset_otp'] = otp
            session['reset_email'] = email

            msg = Message(
                'Password Reset OTP',
                sender='lakshmisatya0613@gmail.com',
                recipients=[email]
            )

            msg.body = f'Your Password Reset OTP is: {otp}'

            mail.send(msg)

            return redirect('/verify_reset_otp')

        else:
            return "Email not found"

    return render_template('forgot_password.html')
@app.route('/verify_reset_otp', methods=['GET', 'POST'])
def verify_reset_otp():

    if request.method == 'POST':

        entered_otp = request.form['otp']

        if entered_otp == session.get('reset_otp'):
            return redirect('/reset_password')

        else:
            return "Invalid OTP"

    return render_template('verify_reset_otp.html')
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():

    if request.method == 'POST':

        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return "Passwords do not match"

        cursor.execute(
            """
            UPDATE students
            SET password=%s
            WHERE email=%s
            """,
            (
                password,
                session['reset_email']
            )
        )

        db.commit()

        return render_template(
    'password_updated.html'
)

    return render_template('reset_password.html')
@app.route('/view_exams')
def view_exams():

    cursor.execute("SELECT * FROM exams")

    exams = cursor.fetchall()

    return render_template(
        'view_exams.html',
        exams=exams
    )
@app.route('/delete_exam/<int:id>')
def delete_exam(id):

    cursor.execute(
        "DELETE FROM exams WHERE id=%s",
        (id,)
    )

    db.commit()

    return redirect('/view_exams')
@app.route('/edit_exam/<int:id>', methods=['GET','POST'])
def edit_exam(id):

    if request.method == 'POST':

        exam_name = request.form['exam_name']
        exam_date = request.form['exam_date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        status = request.form['status']

        cursor.execute(
            """
            UPDATE exams
            SET exam_name=%s,
                exam_date=%s,
                start_time=%s,
                end_time=%s,
                status=%s
            WHERE id=%s
            """,
            (
                exam_name,
                exam_date,
                start_time,
                end_time,
                status,
                id
            )
        )

        db.commit()

        return redirect('/view_exams')

    cursor.execute(
        "SELECT * FROM exams WHERE id=%s",
        (id,)
    )

    exam = cursor.fetchone()

    return render_template(
        'edit_exam.html',
        exam=exam
    )
@app.route('/profile')
def profile():

    email = session.get('email')

    cursor.execute(
        "SELECT * FROM students WHERE email=%s",
        (email,)
    )

    student = cursor.fetchone()

    cursor.execute(
        "SELECT COUNT(*) FROM results WHERE student_email=%s",
        (email,)
    )

    total_attempted = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM exams"
    )

    
    total_exams = cursor.fetchone()[0]
    total_not_attempted=max(0, total_exams-total_attempted)
    return render_template(
        'profile.html',
        student=student,
        total_attempted=total_attempted,
        total_not_attempted=total_not_attempted
    )
@app.route('/admin_analytics')
def admin_analytics():

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM questions")
    total_questions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM exams")
    total_exams = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM results")
    total_attempts = cursor.fetchone()[0]

    return render_template(
        'admin_analytics.html',
        total_students=total_students,
        total_questions=total_questions,
        total_exams=total_exams,
        total_attempts=total_attempts
    )
@app.route('/leaderboard')
def leaderboard():

    cursor.execute("""
    SELECT student_email,
           MAX(score) as best_score
    FROM results
    GROUP BY student_email
    ORDER BY best_score DESC
    """)

    leaders = cursor.fetchall()

    return render_template(
        'leaderboard.html',
        leaders=leaders
    )
@app.route('/dashboard')
def dashboard():

    email = session.get('email')

    cursor.execute(
        "SELECT * FROM students WHERE email=%s",
        (email,)
    )

    student = cursor.fetchone()
    cursor.execute("""
        SELECT *
        FROM exams
        WHERE exam_date = CURDATE()
        AND exam_name NOT IN
(
    SELECT exam_name
    FROM results
    WHERE student_email=%s
)          
        """,(email,))

    live_exams = cursor.fetchall()
    

    

    cursor.execute("""
        SELECT *
        FROM exams
        WHERE exam_date > CURDATE()
        ORDER BY exam_date
        """)

    upcoming_exams = cursor.fetchall()

    cursor.execute("""
        SELECT exam_name
        FROM exams
        WHERE exam_date < CURDATE()
        AND exam_name NOT IN
        (
            SELECT exam_name
            FROM results
            WHERE student_email=%s
        )
        """,(email,))

    not_attempted_exams = cursor.fetchall()
    cursor.execute("""
        SELECT *
        FROM exams
        WHERE exam_date = CURDATE() + INTERVAL 1 DAY
        """)

    tomorrow_exams = cursor.fetchall()
    return render_template(
        'dashboard.html',
        name=student[1],
        live_exams=live_exams,
        upcoming_exams=upcoming_exams,
        not_attempted_exams=not_attempted_exams,
        tomorrow_exams=tomorrow_exams
    )

@app.route('/all_students_results')
def all_students_results():

    cursor = db.cursor()

    cursor.execute("""
        SELECT DISTINCT exam_name
        FROM results
    """)

    exams = cursor.fetchall()

    return render_template(
        'all_students_results.html',
        exams=exams
    )
@app.route('/admin_dashboard')
def admin_dashboard():
    
    return render_template(
        'admin_dashboard.html'
    )
@app.route('/manage_exam/<int:exam_id>')
def manage_exam(exam_id):

    cursor.execute(
        "SELECT * FROM exams WHERE id=%s",
        (exam_id,)
    )

    exam = cursor.fetchone()

    return render_template(
        "manage_exam.html",
        exam=exam
    )

@app.route('/question_count/<int:exam_id>', methods=['GET', 'POST'])
def question_count(exam_id):

    cursor.execute(
        "SELECT exam_name FROM exams WHERE id=%s",
        (exam_id,)
    )

    exam = cursor.fetchone()

    if request.method == 'POST':

        total_questions = int(request.form['count'])

        session['remaining_questions'] = total_questions
        session['total_questions'] = total_questions

        return redirect(
            url_for(
                'add_question',
                exam_id=exam_id
            )
        )

    return render_template(
        'question_count.html',
        exam_name=exam[0]
    )
@app.route('/view_results')
def view_results():

    cursor.execute("""
        SELECT DISTINCT exam_name
        FROM results
        ORDER BY exam_name
    """)

    exams = cursor.fetchall()
    print("EXAMS =",exams)
    return render_template(
        "view_results.html",
        exams=exams
    )
@app.route('/exam_results/<exam_name>')
def exam_results(exam_name):


    sql = """

    SELECT

    students.name,

    students.email,

    results.score

    FROM results

    JOIN students

    ON students.email=results.student_email

    WHERE results.exam_name=%s

    """

    cursor.execute(
        sql,
        (exam_name,)
    )

    results = cursor.fetchall()

    return render_template(
        "exam_results.html",
        exam_name=exam_name,
        results=results
    )
if __name__ == '__main__':
    app.run(debug=True)