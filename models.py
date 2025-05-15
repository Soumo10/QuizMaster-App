from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()  # Instance of SQLAlchemy

class User(db.Model):
    __tablename__ = "user_info"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    pwd = db.Column(db.String, nullable=False) 
    full_name = db.Column(db.String, nullable=True)
    qual = db.Column(db.String, nullable=True)
    dob = db.Column(db.String, nullable=True)
    role = db.Column(db.Integer, nullable=False, default=1)  # 0 for admin, 1 for regular user


# Subject model
class Subject(db.Model):
    __tablename__ = "subjects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)
    desc = db.Column(db.String, nullable=False, unique=True)
    chapters = db.relationship('Chapter', backref='subject', lazy='dynamic')
    
    def __repr__(self):
        return f"Subject('{self.name}')"


# Chapter model
class Chapter(db.Model):
    __tablename__ = "chapters"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    desc = db.Column(db.String, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    
    # Add relationship to questions
    questions = db.relationship('Question', backref='chapter', lazy='dynamic')
    
    def __repr__(self):
        return f"Chapter('{self.name}')"


# Quiz model
class Quiz(db.Model):
    __tablename__ = "quizzes"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    # Rename for clarity - this should be subject_id
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    # Add chapter_id field
    chapter_id = db.Column(db.Integer, db.ForeignKey("chapters.id"), nullable=False)
    duration = db.Column(db.String, nullable=False)  # Store as string (e.g., "00:10")
    created_by_id = db.Column(db.Integer, db.ForeignKey("user_info.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.String, nullable=False, default=datetime.now().strftime("%Y-%m-%d"))

    # Update relationship names
    subject = db.relationship("Subject", backref="quizzes")
    chapter = db.relationship("Chapter", backref="quizzes")
    created_by = db.relationship("User", backref="quizzes_created")
    
    def __repr__(self):
        return f"Quiz('{self.title}', duration: {self.duration})"


# Question model
class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey("chapters.id"), nullable=False)
    question_text = db.Column(db.String, nullable=False)
    
    # Update relationships
    quiz = db.relationship("Quiz", backref="questions")
    options = db.relationship("Option", backref="question", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"Question('{self.question_text[:20]}...')"


# Option model
class Option(db.Model):
    __tablename__ = "options"
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    option_text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"Option('{self.option_text}', correct: {self.is_correct})"


# Score model to track user performance on quizzes
class Score(db.Model):
    __tablename__ = "scores"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user_info.id"), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    score = db.Column(db.Float, nullable=False)  # Score as a percentage
    attempt_date = db.Column(db.String, nullable=False)  # Store as string (e.g., "2025-03-01")

    user = db.relationship("User", backref="scores")
    quiz = db.relationship("Quiz", backref="scores")
    
    def __repr__(self):
        return f"Score({self.user_id}, {self.quiz_id}, {self.score}%)"


# QuizAttempt model to track number of attempts per user per quiz
class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user_info.id"), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    attempt_count = db.Column(db.Integer, default=0)
    last_attempt_date = db.Column(db.String, nullable=False)  # Store as string (e.g., "2025-03-01")

    user = db.relationship("User", backref="quiz_attempts")
    quiz = db.relationship("Quiz", backref="quiz_attempts")
    
    def __repr__(self):
        return f"QuizAttempt({self.user_id}, {self.quiz_id}, attempts: {self.attempt_count})"