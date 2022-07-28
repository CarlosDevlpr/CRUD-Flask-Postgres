from src.models.user import UsersModel
from src.schemas.user import CreatedUser
from flask import request
from werkzeug.security import generate_password_hash
from sqlalchemy import  or_
from src.utils import BaseService, Forbidden

class UserService(BaseService):
	def __init__(self, session):
		super(UserService, self).__init__(session)

	def commit_user(self):
		user = UsersModel(**request.body_params.dict())
		user.password = generate_password_hash(user.password)
		self.session.add(user)
		self.session.commit()
		return CreatedUser(username=user.username, email=user.email)

	def user_exists(self, username, email):
		return bool(UsersModel.query.filter(or_(UsersModel.username == str(username),UsersModel.email == str(email))).first())

	def create_user(self, *, username, email, password):
		if self.user_exists(username, email):
			raise Forbidden('this user already exists')
		return self.commit_user()