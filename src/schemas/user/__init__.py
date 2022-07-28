from pydantic import BaseModel as BaseModelPY

#Para a rota de criar os usuários
class CreateUser(BaseModelPY):
    username: str
    email: str
    password: str

#Para pesquisar os usuários
class CreatedUser(BaseModelPY):
    username: str
    email: str

#Para validar as requisições
class ForBody(BaseModelPY):
    param: str
