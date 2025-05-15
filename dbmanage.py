from backend.models import *
from app import *
db.create_all()
usr=User(id=0,email="soumo123@gmail.com",pwd="12345",role=0)
db.session.add(usr)
db.session.commit()