from flask import Flask, render_template, request, redirect, url_for
from flask import current_app as app
from datetime import date
import os
from sqlalchemy import func
from collections import defaultdict
from datetime import datetime

#imports for graph
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

from .models import *
db.create_all()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        email = request.form.get("email")
        pwd = request.form.get("pwd")
        usr = User.query.filter_by(email=email).first() #LHS is attribute name in table and RHS is data fetched from form
        # Add password verification
        if usr and usr.pwd == pwd:  # Verify password matches
            if usr.role == 0:  # Admin
                print("logged in as Admin")
                return redirect(url_for('admin_dashboard', email=usr.email))
            elif usr.role == 1:  # Regular user
                print("logged in as User")
                scores = Score.query.filter_by(user_id=usr.id).all()
                # Fetch all active quizzes
                quizzes = Quiz.query.filter_by(is_active=True).all()
                return redirect(url_for('user_dash', email=usr.email))

        return render_template("login.html", msg="Invalid Credentials")
    
    return render_template("login.html")



@app.route("/signup", methods=["GET", "POST"])
def user_signup():
    if request.method == "POST":
        email = request.form.get("email")
        full_name = request.form.get("full_name")
        qual = request.form.get("qual")
        dob = request.form.get("dob")
        pwd = request.form.get("pwd")
        
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            return render_template("login.html", msg="User already exists,Please login")
        
        new_user = User(email=email, full_name=full_name, dob=dob, qual=qual, pwd=pwd, role=1)
        db.session.add(new_user)
        db.session.commit()
        print(f"User {email} created successfully")

        return redirect(url_for("user_login", msg="Signup successful! Please login."))
        
    return render_template("signup.html", msg="")


@app.route("/admin_dash")
def admin_dashboard():
    email = request.args.get('email')
    user = User.query.filter_by(email=email).first()
    name = user.full_name if user else "Admin"
    subjects = Subject.query.all()
    return render_template("admin_dash.html", name=name, subjects=subjects, users={}, msg="", email=email)

# Route for Quiz Management
@app.route("/quiz-mgmt")
def quiz_management():
    # Fetching all quiz attempts with related data
    all_attempts = Score.query.join(User).join(Quiz, isouter=True).join(Subject, isouter=True).join(Chapter, isouter=True).order_by(Score.attempt_date.asc()).all()
    
    # Dictionary to store the attempt count for each (user, quiz) combination
    attempt_counts = {}
    
    # Filtering out attempts with incomplete data
    filtered_attempts = []
    for attempt in all_attempts:
        # Checking if the attempt has all required relationships
        if attempt.user and attempt.quiz and attempt.quiz.subject and attempt.quiz.chapter:
            key = (attempt.user_id, attempt.quiz_id)
            if key not in attempt_counts:
                attempt_counts[key] = 0
            attempt_counts[key] += 1
            # Attaching the attempt number to the attempt object
            attempt.attempt_number = attempt_counts[key]
            filtered_attempts.append(attempt)
        else:
            # Log incomplete attempts for debugging
            print(f"Incomplete attempt: User={attempt.user}, Quiz={attempt.quiz}")
    
    # Sorting attempts by attempt_date (newest first) for display
    filtered_attempts.sort(key=lambda x: x.attempt_date, reverse=True)
    
    # Passing the email from request args as name for consistency
    name = request.args.get('email', 'Admin')
    
    return render_template("quiz-mgmt.html", name=name, attempts=filtered_attempts)


#Route to show users in admin dashboard
@app.route("/show_user")
def show_user():
    # Fetch all users from the database
    users = User.query.filter_by(role=1).all()  # Filter for regular users (role=1)
    return render_template("show_user.html", users=users, name=request.args.get('email', 'Admin'))

# Route to delete a user
@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Delete related scores first
    Score.query.filter_by(user_id=user_id).delete()
    
    # Delete related quiz attempts
    QuizAttempt.query.filter_by(user_id=user_id).delete()
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    print(f"User {user.email} deleted successfully")
    
    return redirect(url_for("show_user"))


#Route for Admin Search
@app.route('/admin/search')
def admin_search():
    query = request.args.get('query', '').strip()
    
    # Initialize empty lists for results
    users, subjects, quizzes = [], [], []
    
    if query:
        # Search users by name, email
        users = User.query.filter(
            db.or_(
                User.full_name.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%")
            )
        ).filter_by(role=1).all()  # Only regular users
        
        # Searching subjects by name
        subjects = Subject.query.filter(Subject.name.ilike(f"%{query}%")).all()
        
        # Searching quizzes by name
        quizzes = Quiz.query.filter(Quiz.title.ilike(f"%{query}%")).all()
    
    # Fetching additional details for rendering
    user_data = []
    for user in users:
        user_quizzes = QuizAttempt.query.filter_by(user_id=user.id).all()
        user_data.append({
            'user': user,
            'quiz_attempts': [
                {
                    'quiz': attempt.quiz,
                    'subject': attempt.quiz.subject,
                    'chapter': attempt.quiz.chapter
                } for attempt in user_quizzes
            ]
        })
    
    # Fetching chapters and quizzes for subjects
    subject_data = []
    for subject in subjects:
        chapters = Chapter.query.filter_by(subject_id=subject.id).all()
        subject_data.append({
            'subject': subject,
            'chapters': [
                {
                    'chapter': chapter,
                    'quizzes': Quiz.query.filter_by(chapter_id=chapter.id).all()
                } for chapter in chapters
            ]
        })
    
    # Fetching subject and chapter details for quizzes
    quiz_data = []
    for quiz in quizzes:
        quiz_data.append({
            'quiz': quiz,
            'subject': quiz.subject,
            'chapter': quiz.chapter
        })
    
    return render_template('admin_dash.html', 
                            query=query, 
                            user_data=user_data, 
                            subject_data=subject_data, 
                            quiz_data=quiz_data,
                            subjects=Subject.query.all())  


#Route for User Search
@app.route('/user/search')
def user_search():
    email = request.args.get('email')
    query = request.args.get('query', '').strip()
    
    # Validate email and fetch user
    if not email:
        print("No email provided in search request")
        return redirect(url_for('user_login'))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        print(f"No user found for email: {email}")
        return redirect(url_for('user_login'))
    
    print(f"Processing search for user: {user.email}, query: '{query}'")
    
    # Base query for scores
    scores_query = Score.query.filter_by(user_id=user.id)
    
    # Apply search filters if query exists
    if query:
        scores = scores_query.join(Quiz).join(Subject, isouter=True).join(Chapter, isouter=True).filter(
            db.or_(
                Subject.name.ilike(f"%{query}%"),
                Chapter.name.ilike(f"%{query}%"),
                Quiz.title.ilike(f"%{query}%"),
                Score.attempt_date.ilike(f"%{query}%")
            )
        ).all()
    else:
        scores = scores_query.all()
    
    # Checking scores and their relationships
    filtered_scores = []
    for score in scores:
        try:
            # Each score has a valid quiz and subject
            if score.quiz and score.quiz.subject:
                filtered_scores.append(score)
            else:
                print(f"Skipping score {score.id}: Missing quiz or subject")
        except Exception as e:
            print(f"Error processing score {score.id}: {e}")
    
    # Fetching attempt counts
    attempts = QuizAttempt.query.filter_by(user_id=user.id).all()
    attempts_dict = {attempt.quiz_id: attempt.attempt_count for attempt in attempts}
    
    # More debug information
    print(f"Total scores found: {len(scores)}")
    print(f"Filtered scores: {len(filtered_scores)}")
    
    # Render template with filtered scores
    return render_template('quiz_scores.html',
                          user=user,
                          scores=filtered_scores,
                          attempts=attempts_dict,
                          email=email,
                          query=query)



@app.route("/user_dash", endpoint='user_dash')
def user_dashboard():
    email = request.args.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect(url_for('user_login'))
        
    # Fetch all active quizzes
    quizzes = Quiz.query.filter_by(is_active=True).all()
    scores = Score.query.filter_by(user_id=user.id).all()
    
    return render_template("user_dash.html", 
                           user=user, 
                           full_name=user.full_name, 
                           scores=scores, 
                           quizzes=quizzes, 
                           msg=request.args.get('msg', ''))


# Routes for Subjects (Admin functionality)
@app.route("/new-subject", methods=["GET", "POST"])
def manage_subjects():
    if request.method == "POST":
        subject_name = request.form.get("name")
        description = request.form.get("desc") # Add this line for debugg
        if not subject_name:
            return render_template("new-subject.html", msg="Please enter a subject name")
        
        new_subject = Subject(name=subject_name, desc=description)
        db.session.add(new_subject)
        db.session.commit()
        print(f"Subject {subject_name} created successfully")
        return redirect(url_for("admin_dashboard"))
    
    subjects = Subject.query.all()
    return render_template("new-subject.html", subjects=subjects, msg="")

# Route to handle showing chapters for a specific subject
@app.route("/show_chapters/<int:subject_id>")
def show_chapters(subject_id):
    # Get the subject
    subject = Subject.query.get_or_404(subject_id)
    
    # Get name from email or use default
    email = request.args.get('email')
    user = User.query.filter_by(email=email).first()
    name = user.full_name if user else "Admin"
    
    # Get all chapters for this subject
    chapters = Chapter.query.filter_by(subject_id=subject_id).all()
    
    return render_template("show_chapters.html", subject=subject, chapters=chapters, name=name)


# Route to edit a subject 
@app.route('/edit_subject/<int:subject_id>', methods=['POST'])
def edit_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    # Get form data
    new_name = request.form.get("name")
    new_desc = request.form.get("desc")
    
    if new_name:
        subject.name = new_name
    if new_desc:
        subject.desc = new_desc
        
    db.session.commit()
    print(f"Subject {subject_id} updated to {new_name}")
    
    return redirect(url_for("admin_dashboard"))

# Route to Delete a Subject
@app.route('/delete_subject/<int:subject_id>')  # Add this route decorator
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    # Delete related chapters first
    for chapter in subject.chapters:
        db.session.delete(chapter)
    db.session.delete(subject)
    db.session.commit()
    print(f"Subject {subject.name} deleted successfully")
    return redirect(url_for("admin_dashboard"))

# Routes for Chapters (Admin functionality)
@app.route('/new-chapter/<int:subject_id>', methods=['GET', 'POST'])
def new_chapter(subject_id):
    if request.method == "POST":
        name = request.form.get("name")
        desc = request.form.get("desc")
        print(f"Received data: name={name}, desc={desc}")
        if not name or not desc:
            return render_template("new-chapter.html", subject_id=subject_id, msg="Please fill all fields")
            
        new_chapter = Chapter(name=name, desc=desc, subject_id=subject_id)
        db.session.add(new_chapter)
        db.session.commit()
        print(f"Chapter {name} created successfully for subject {subject_id}")
        return redirect(url_for("show_chapters", subject_id=subject_id))
    # Pass the subject_id to the template
    return render_template("new-chapter.html", subject_id=subject_id, msg="")

# Route to handle showing quizzes for a specific chapter
@app.route("/show_quiz/<int:subject_id>/<int:chapter_id>")
def show_quizzes(subject_id, chapter_id):
    # Get the subject and chapter
    subject = Subject.query.get_or_404(subject_id)
    chapter = Chapter.query.get_or_404(chapter_id)
    
    # Get name from email or use default
    email = request.args.get('email')
    user = User.query.filter_by(email=email).first()
    name = user.full_name if user else "Admin"
    
    # Get all quizzes for this chapter
    quizzes = Quiz.query.filter_by(chapter_id=chapter_id).all()
    
    return render_template("show_quiz.html", subject=subject, chapter=chapter, quizzes=quizzes, name=name)


# Route to edit a chapter 
@app.route('/edit_chapter/<int:chapter_id>', methods=['POST'])
def edit_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    new_name = request.form.get('name')
    new_desc = request.form.get('desc')
    try:
        if new_name:
            chapter.name = new_name
        if new_desc:
            chapter.desc = new_desc
        db.session.commit()
        print(f"Chapter {chapter_id} updated to {new_name} with desc {new_desc}")
    except Exception as e:
        db.session.rollback()
        print(f"Error updating chapter: {e}")
        return render_template("show_chapters.html", subject=chapter.subject, chapters=Chapter.query.filter_by(subject_id=chapter.subject_id).all(), name=request.args.get('email'), msg="Error updating chapter")
    
    return redirect(url_for('show_chapters', subject_id=chapter.subject_id))

# Route to delete a chapter
@app.route('/delete_chapter/<int:chapter_id>')
def delete_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    Quiz.query.filter_by(chapter_id=chapter.id).delete()
    Question.query.filter_by(chapter_id=chapter.id).delete()
    db.session.delete(chapter)
    db.session.commit()
    return redirect(url_for('show_chapters', subject_id=chapter.subject_id))


# Routes for Quizzes (Admin functionality)
@app.route('/new_quiz/<int:subject_id>/<int:chapter_id>', methods=['GET', 'POST'])
def new_quiz(subject_id, chapter_id):
    subject = Subject.query.get_or_404(subject_id)
    chapter = Chapter.query.get_or_404(chapter_id)
    
    if request.method == 'POST':
        title = request.form['title']
        duration = request.form['duration']
        is_active = 'is_active' in request.form  # Checkbox
        
        # Correct usage: use chapter_id, not chapter_name
        quiz = Quiz(
            title=title,
            subject_id=subject_id,
            chapter_id=chapter_id,  # Use chapter_id from URL parameter
            duration=duration,
            created_by_id=1,  # Replace with actual user ID (e.g., from session)
            is_active=is_active
        )
        
        # try:
        db.session.add(quiz)
        db.session.commit()
            # flash('Quiz created successfully!', 'success')
        return redirect(url_for('show_quizzes', subject_id=subject_id, chapter_id=chapter_id))
        # except Exception as e:
        #     db.session.rollback()
        #     flash(f'Error creating quiz: {str(e)}', 'error')
    
    return render_template('new-quiz.html', subject=subject, chapter=chapter)



# Route to edit a Quiz
@app.route('/edit_quiz/<int:quiz_id>', methods=['POST'])
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Get form data
    new_title = request.form.get('title')
    new_duration = request.form.get('duration')
    is_active = 'is_active' in request.form
    
    # Update quiz properties
    if new_title:
        quiz.title = new_title
    if new_duration:
        quiz.duration = new_duration
    
    quiz.is_active = is_active
    
    db.session.commit()
    print(f"Quiz {quiz_id} updated successfully")
    
    # Redirect back to show_quiz
    return redirect(url_for('show_quizzes', subject_id=quiz.subject_id, chapter_id=quiz.chapter_id))


# Route to delete a Quiz
@app.route('/delete_quiz/<int:quiz_id>')
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Store the chapter_id and subject_id for redirect
    chapter_id = quiz.chapter_id
    subject_id = quiz.subject_id
    
    # Delete related questions and options first
    for question in Question.query.filter_by(quiz_id=quiz_id).all():
        Option.query.filter_by(question_id=question.id).delete()
    
    Question.query.filter_by(quiz_id=quiz_id).delete()
    
    # Delete the quiz
    db.session.delete(quiz)
    db.session.commit()
    
    print(f"Quiz {quiz_id} deleted successfully")
    
    # Redirect back to show_quizzes
    return redirect(url_for('show_quizzes', subject_id=subject_id, chapter_id=chapter_id))


# Route for adding a new question
@app.route("/new-question/<int:quiz_id>", methods=["GET", "POST"])
def new_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    msg = ""

    if request.method == "POST":
        question_text = request.form.get("question_text")
        if not question_text:
            msg = "Question text is required"
            questions = Question.query.filter_by(quiz_id=quiz_id).all()
            subjects = Subject.query.all()
            return render_template("new-question.html", quiz=quiz, questions=questions, subjects=subjects, msg=msg)

        # Get chapter_id from the quiz object
        chapter_id = quiz.chapter_id  

        # Create new question with quiz_id and chapter_id
        new_question = Question(quiz_id=quiz_id, chapter_id=chapter_id, question_text=question_text)
        db.session.add(new_question)
        db.session.commit()

        # Handle options
        options = {
            'A': request.form.get("option_text_A"),
            'B': request.form.get("option_text_B"),
            'C': request.form.get("option_text_C"),
            'D': request.form.get("option_text_D")
        }
        correct_option = request.form.get("correct_option")

        # Validate options
        if not all(options.values()):
            db.session.rollback()
            msg = "All options must be filled"
            questions = Question.query.filter_by(quiz_id=quiz_id).all()
            subjects = Subject.query.all()
            return render_template("new-question.html", quiz=quiz, questions=questions, subjects=subjects, msg=msg)

        # Save options
        for letter, text in options.items():
            is_correct = (letter == correct_option)
            new_option = Option(
                question_id=new_question.id,
                option_text=text,
                is_correct=is_correct
            )
            db.session.add(new_option)

        db.session.commit()
        msg = "Question and options created successfully"
        return redirect(url_for('manage_questions', quiz_id=quiz_id))

    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    subjects = Subject.query.all()
    return render_template("new-question.html", quiz=quiz, questions=questions, subjects=subjects, msg=msg)


# Route to show questions for a specific quiz
@app.route('/manage_questions/<int:quiz_id>')
def manage_questions(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    
    # Load options for each question
    for question in questions:
        question.options = Option.query.filter_by(question_id=question.id).all()
    
    return render_template('show_question.html', quiz=quiz, questions=questions, name=request.args.get('email', 'Admin'))

# Route to edit a question
@app.route('/edit_question/<int:question_id>', methods=['POST'])
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    
    # Get form data
    question_text = request.form.get('question_text')
    hint = request.form.get('hint', '')
    
    # Update question text and hint
    if question_text:
        question.question_text = question_text
        question.hint = hint
        db.session.commit()
        print(f"Question {question_id} updated successfully")
    
    # Get correct option letter
    correct_option_letter = request.form.get('correct_option')
    
    # Update each option (A, B, C, D)
    for letter in ['A', 'B', 'C', 'D']:
        option_text = request.form.get(f'option_text_{letter}')
        option_id = request.form.get(f'option_id_{letter}')
        
        if option_id and option_id.strip():
            # Update existing option
            option = Option.query.get(int(option_id))
            if option:
                option.option_text = option_text
                option.is_correct = (letter == correct_option_letter)
        else:
            # Create new option
            new_option = Option(
                question_id=question_id,
                option_text=option_text,
                is_correct=(letter == correct_option_letter)
            )
            db.session.add(new_option)
    
    db.session.commit()
    print(f"Options for question {question_id} updated successfully")
    
    # Redirect back to the questions page
    return redirect(url_for('manage_questions', quiz_id=question.quiz_id))


# Route to delete a question
@app.route('/delete_question/<int:question_id>')
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz_id = question.quiz_id
    
    # Delete all options for this question first
    Option.query.filter_by(question_id=question_id).delete()
    
    # Delete the question
    db.session.delete(question)
    db.session.commit()
    print(f"Question {question_id} deleted successfully")
    
    # Redirect back to the questions page
    return redirect(url_for('manage_questions', quiz_id=quiz_id))


# User part Routes


# Routes for User Taking Quiz (User functionality)
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from datetime import date, datetime, timedelta

@app.route("/user/quiz/<int:quiz_id>", methods=["GET", "POST"])
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    email = request.args.get('email') if request.method == "GET" else request.form.get('email')
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect(url_for('user_login'))
    
    if request.method == "POST":
        # Start time for time taken calculation (assuming it’s passed via a hidden input)
        start_time_str = request.form.get('start_time')
        start_time = datetime.fromtimestamp(float(start_time_str)) if start_time_str else datetime.now()
        
        # Calculate score and correct answers
        score = 0
        questions = Question.query.filter_by(quiz_id=quiz_id).all()
        total_questions = len(questions)
        
        for question in questions:
            selected_option_id = request.form.get(f"question_{question.id}")
            if selected_option_id:
                selected_option = Option.query.get(selected_option_id)
                if selected_option and selected_option.is_correct:
                    score += 1

        # Calculate percentage for Score model
        final_score = (score / total_questions) * 100 if total_questions > 0 else 0
        
        # Calculate time taken
        end_time = datetime.now()
        time_taken = end_time - start_time
        minutes = time_taken.seconds // 60
        seconds = time_taken.seconds % 60
        time_taken_str = f"{minutes} minutes {seconds} seconds"
        
        # Record score and attempt
        new_score = Score(user_id=user.id, quiz_id=quiz_id, score=final_score, attempt_date=str(date.today()))
        quiz_attempt = QuizAttempt.query.filter_by(user_id=user.id, quiz_id=quiz_id).first()
        if quiz_attempt:
            quiz_attempt.attempt_count += 1
            quiz_attempt.last_attempt_date = str(date.today())
        else:
            quiz_attempt = QuizAttempt(user_id=user.id, quiz_id=quiz_id, attempt_count=1, last_attempt_date=str(date.today()))
        
        try:
            db.session.add(new_score)
            db.session.add(quiz_attempt)
            db.session.commit()
            print(f"Quiz {quiz_id} completed with score {final_score}")
        except Exception as e:
            db.session.rollback()
            print(f"Error recording score: {e}")
            return render_template("take_quiz.html", msg="Error submitting quiz", quiz=quiz, questions=questions, email=email)
        
        # Prepare data for the summary table
        summary_data = {
            'subject_name': quiz.subject.name,
            'chapter_name': quiz.chapter.name,
            'time_taken': time_taken_str,
            'attempt_date': str(date.today()),
            'correct_answers': f"{score}/{total_questions}"
        }
        
        # Render the summary template instead of redirecting
        return render_template("quiz_result.html",user=user, quiz=quiz, summary_data=summary_data, email=email)
    
    # GET request - display the quiz
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    for question in questions:
        question.options = Option.query.filter_by(question_id=question.id).all()
    
    # Pass start time to the template for POST calculation
    start_time = datetime.now().timestamp()
    return render_template("take_quiz.html", quiz=quiz, questions=questions, msg="", email=email, start_time=start_time)


# Routes for Quiz Scores (User functionality)
@app.route("/quiz_scores")
def quiz_scores():
    email = request.args.get('email')
    
    # If no email is provided, try to redirect to user login
    if not email:
        return redirect(url_for('user_login'))
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        print(f"No user found for email: {email}")  # Debugging
        return redirect(url_for('user_login'))
    
    # Get all scores for this user
    scores = Score.query.filter_by(user_id=user.id).all()
    
    # Get attempt counts for each quiz
    attempts = QuizAttempt.query.filter_by(user_id=user.id).all()
    
    # Create a dictionary to pass attempts to the template
    attempts_dict = {attempt.quiz_id: attempt.attempt_count for attempt in attempts}
    
    print(f"Rendering quiz_scores for user: {user.email} with {len(scores)} scores")  # Debugging
    return render_template('quiz_scores.html', 
                           user=user, 
                           scores=scores, 
                           attempts=attempts_dict, 
                           email=email)


# NEWLY ADDED ROUTES FOR QUIZ INTERFACE
#View Quiz Route
@app.route('/view_quiz/<int:quiz_id>')
def view_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    email = request.args.get('email')
    print(f"Email parameter received: {email}")  # Debug print
    
    user = User.query.filter_by(email=email).first()
    print(f"User found: {user}")  # Debug print
    
    if not user:
        print("No user found, redirecting to login")  # Debug print
        return redirect(url_for('user_login'))
    
    return render_template('view_quiz.html', quiz=quiz, email=email, user=user)


# Display Quiz Question
@app.route('/quiz/<int:quiz_id>/question/<int:question_number>')
def quiz_question(quiz_id, question_number):
    quiz = Quiz.query.get_or_404(quiz_id)
    email = request.args.get('email')
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return redirect(url_for('user_login'))
    
    # Get all questions for this quiz
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    total_questions = len(questions)
    
    # Check if question exists
    if question_number > total_questions or question_number < 1:
        return redirect(url_for('user_dash', email=email))
    
    # Get the current question (adjust for 0-indexing)
    question = questions[question_number - 1]
    
    # Get question options
    options = Option.query.filter_by(question_id=question.id).all()
    
    # Get user answers from URL parameters
    user_answers = []
    for i in range(total_questions):
        param_name = f'answer_{i+1}'
        if param_name in request.args:
            user_answers.append(int(request.args.get(param_name)))
        else:
            user_answers.append(None)
    
    # Calculate time left
    start_time = datetime.fromtimestamp(float(request.args.get('start_time')))
    end_time = datetime.fromtimestamp(float(request.args.get('end_time')))
    time_left = end_time - datetime.now()
    
    # Format time left for display
    minutes = time_left.seconds // 60
    seconds = time_left.seconds % 60
    time_left_str = f"{minutes:02d}:{seconds:02d}"
    
    # Check if time is up
    if time_left.total_seconds() <= 0:
        # Auto-submit the quiz
        return redirect(url_for('submit_quiz', 
                               quiz_id=quiz_id,
                               email=email,
                               **{f'answer_{i+1}': ans for i, ans in enumerate(user_answers) if ans is not None}))
    
    return render_template('quiz_ques.html',
                          quiz=quiz,
                          question=question,
                          options=options,
                          current_question=question_number,
                          total_questions=total_questions,
                          user_answers=user_answers,
                          time_left=time_left_str,
                          show_progress_bar=True,
                          email=email)




@app.route("/summary")
def summary_charts():
    # Debugging - print received email
    email = request.args.get('email')
    print(f"Received email in summary route: {email}")  # Debug line
    
    if not email:
        print("No email provided in summary request")  # Debug line
        return redirect(url_for('user_login'))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        print(f"No user found for email: {email}")  # Debug line
        return redirect(url_for('user_login'))
    
    print(f"User found: {user.email}, role: {user.role}")  # Debug line
    
    is_admin = user.role == 0
    
    try:
        if is_admin:
            # ADMIN VIEW
            # Subject-wise top scores (bar chart)
            admin_bar_data = db.session.query(
                Subject.name,
                func.max(Score.score).label('top_score')
            ).join(Quiz, Score.quiz_id == Quiz.id)\
             .join(Chapter, Quiz.chapter_id == Chapter.id)\
             .join(Subject, Chapter.subject_id == Subject.id)\
             .group_by(Subject.name).all()
            
            # Subject-wise user attempts (pie chart)
            admin_pie_data = db.session.query(
                Subject.name,
                func.count(Score.id).label('attempt_count')
            ).join(Quiz, Score.quiz_id == Quiz.id)\
             .join(Chapter, Quiz.chapter_id == Chapter.id)\
             .join(Subject, Chapter.subject_id == Subject.id)\
             .group_by(Subject.name).all()
            
            # Generate bar chart
            plt.figure(figsize=(10, 6))
            plt.bar([item[0] for item in admin_bar_data], 
                   [item[1] for item in admin_bar_data], 
                   color='skyblue')
            plt.title('Subject-wise Top Scores', fontsize=15)
            plt.xlabel('Subjects', fontsize=12)
            plt.ylabel('Top Score (%)', fontsize=12)
            plt.xticks(rotation=45)
            plt.tight_layout()
            bar_path = f"static/summary_{user.id}_bar.png"
            plt.savefig(bar_path)
            plt.close()
            
            # Generate pie chart
            plt.figure(figsize=(8, 8))
            plt.pie([item[1] for item in admin_pie_data], 
                   labels=[item[0] for item in admin_pie_data], 
                   autopct='%1.1f%%',
                   startangle=140)
            plt.title('Subject-wise User Attempts', fontsize=15)
            plt.axis('equal')
            plt.tight_layout()
            pie_path = f"static/summary_{user.id}_pie.png"
            plt.savefig(pie_path)
            plt.close()
            
            chart_titles = {
                'bar_title': 'Subject-wise Top Scores',
                'pie_title': 'Subject-wise User Attempts'
            }
            
        else:

            # USER VIEW
            # Subject-wise quiz attempts (bar chart)
            user_bar_data = db.session.query(
                Subject.name,
                func.count(Score.id).label('attempt_count')
            ).join(Quiz, Score.quiz_id == Quiz.id)\
             .join(Chapter, Quiz.chapter_id == Chapter.id)\
             .join(Subject, Chapter.subject_id == Subject.id)\
             .filter(Score.user_id == user.id)\
             .group_by(Subject.name).all()
            
            # Month-wise quiz attempts (pie chart)
            user_pie_data = db.session.query(
                func.strftime('%Y-%m', Score.attempt_date).label('month'),
                func.count(Score.id).label('attempt_count')
            ).filter(Score.user_id == user.id)\
             .group_by('month').all()
            
            # Generate bar chart
            plt.figure(figsize=(10, 6))
            plt.bar([item[0] for item in user_bar_data], 
                   [item[1] for item in user_bar_data], 
                   color='lightgreen')
            plt.title('Subject-wise Quizzes Attempted', fontsize=15)
            plt.xlabel('Subjects', fontsize=12)
            plt.ylabel('Number of Quizzes', fontsize=12)
            plt.xticks(rotation=45)
            plt.tight_layout()
            bar_path = f"static/summary_{user.id}_bar.png"
            plt.savefig(bar_path)
            plt.close()
            
            # Generate pie chart
            plt.figure(figsize=(8, 8))
            plt.pie([item[1] for item in user_pie_data], 
                   labels=[item[0] for item in user_pie_data], 
                   autopct='%1.1f%%',
                   startangle=140)
            plt.title('Month-wise Quizzes Attempted', fontsize=15)
            plt.axis('equal')
            plt.tight_layout()
            pie_path = f"static/summary_{user.id}_pie.png"
            plt.savefig(pie_path)
            plt.close()
            
            chart_titles = {
                'bar_title': 'Subject-wise Quizzes Attempted',
                'pie_title': 'Month-wise Quizzes Attempted'
            }
            
    except Exception as e:
        print(f"Error generating charts: {e}")
        return render_template('error.html', error_message="Error generating charts")
    
    return render_template('summary_charts.html',
                         name=user.full_name,
                         email=email,
                         is_admin=is_admin,
                         user_id=user.id,
                         chart_titles=chart_titles)