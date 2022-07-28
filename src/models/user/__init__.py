from src import * 
from src.utils.bases import BaseEntity

db = db

#Crie suas tabelas com essas bases
class UsersTable(BaseEntity):
	__tablename__ = 'users'

	fullname = db.Column(db.String(200))
	email = db.Column(db.String(200))
	password = db.Column(db.String(250))

	class Config:
		orm_mode = True
