from pydantic import BaseModel as BaseModelPY
from typing import List

#Para a rota de criar os usuários
class CreateUser(BaseModelPY):
    username: str
    email: str
    password: str

#Para pesquisar os usuários de forma pública
class CreatedUser(BaseModelPY):
    username: str
    email: str

#Para retornar listas de usuários pública
class UsersList(BaseModelPY):
    users: List[CreatedUser]

#Para validar as requisições
class ForBody(BaseModelPY):
    param: str
