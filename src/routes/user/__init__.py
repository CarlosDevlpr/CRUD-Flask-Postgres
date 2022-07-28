from src import app 
from src.services.user import UserService
from src.schemas.user import  CreatedUser, CreateUser
from src.utils import validate, db, request

@app.route('/v1/user/create', methods=['POST'])
@validate(body = CreateUser, response_model = CreatedUser)
def create_user():
	return UserService(db.session).create_user(**request.body_params.dict())