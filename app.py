from flask import Flask
from backend.models import*

app=None #initially none

def init_app():
    QuizMaster=Flask(__name__) #object of Flask
    QuizMaster.debug=True
    QuizMaster.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///Quiz.sqlite3"
    QuizMaster.app_context().push() #Direct access App
    db.init_app(QuizMaster) #object.method(<parameter>)
    db.create_all()
    print("Quiz Master App Started")
    return QuizMaster

app=init_app()
from backend.controllers import*
if __name__=="__main__":
    app.run(debug=True)