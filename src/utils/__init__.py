from functools import wraps
from typing import (Any, Callable, Iterable, List, Optional, Type, TypeVar, Union)

from flask import Response, make_response, request
from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError
from pydantic.errors import PydanticValueError
from sqlalchemy.exc import SQLAlchemyError
from src import db
from src.utils.bases import BaseEntity
from src.utils.bases import BaseModel as BaseModelDB
from src.utils.bases import ErrorSchema

T = TypeVar("T")

class BaseService:
    def __init__(self, session):
        self.session = session

class HTTPError(Exception):
    """Base exception for requests that go wrong"""

    def __init__(self, message, code):
        self.message = message
        self.code = code

class NotFound(HTTPError):
    """Exception raised for when an object was not found"""
    
    def __init__(self, message):
        self.code = 404
        super().__init__(message, self.code)

class Forbidden(HTTPError):
    """Exception raised for when an object was not found"""
    
    def __init__(self, message):
        self.code = 403
        super().__init__(message, self.code)


class BaseFlaskPydanticException(Exception):
    """Base exc class for all exception from this library"""


class InvalidIterableOfModelsException(BaseFlaskPydanticException):
    """This exception is raised if there is a failure during serialization of
    response object with `response_many=True`"""


class ManyModelValidationError(BaseFlaskPydanticException):
    """This exception is raised if there is a failure during validation of many
    models in an iterable"""

    def __init__(self, errors: List[dict], *args):
        self._errors = errors
        super().__init__(*args)

    def errors(self):
        return self._errors


def make_json_response(
    content: Union[BaseModel, Iterable[BaseModel]],
    status_code: int,
    *,
    exclude_none: bool = False,
    many: bool = False,
    response_model: Optional[Type[BaseModel]] = None,
) -> Response:
    """serializes model, creates JSON response with given status code"""
    if response_model:
        serialize = response_model.from_orm if response_model.Config.orm_mode else response_model.parse_obj
        if many:
            js = f"[{', '.join([serialize(item).json(exclude_none=exclude_none) for item in content])}]"
        else:
            js = serialize(content).json(exclude_none=exclude_none)
    else:
        if many:
            js = f"[{', '.join([model.json(exclude_none=exclude_none) for model in content])}]"
        else:
            js = content.json(exclude_none=exclude_none)
    response = make_response(js, status_code)
    response.mimetype = "application/json"
    return response


def is_iterable_of_models(content: Any) -> bool:
    try:
        return (
            all(isinstance(obj, BaseModel) for obj in content)
            or all(isinstance(obj, BaseEntity) for obj in content)
            or all(isinstance(obj, BaseModelDB) for obj in content)
        )
    except TypeError:
        return False


def validate_many_models(model: Type[BaseModel], content: Any) -> List[BaseModel]:
    try:
        return [model(**fields) for fields in content]
    except TypeError:
        # iteration through `content` fails
        err = [
            {
                "loc": ["root"],
                "msg": "is not an array of objects",
                "type": "type_error.array",
            }
        ]
        raise ManyModelValidationError(err)
    except ValidationError as ve:
        raise ManyModelValidationError(ve.errors())


def normalize_query_param(value):
    """
    Given a non-flattened query parameter value,
    and if the value is a list only containing 1 item,
    then the value is flattened.
    :param value: a value from a query parameter
    :return: a normalized query parameter value
    """
    return value if len(value) > 1 else value[0]


def normalize_query(params):
    """
    Converts query parameters from only containing one value for each parameter,
    to include parameters with multiple values as lists.
    :param params: a flask query parameters data structure
    :return: a dict of normalized query parameters
    """
    params_non_flat = params.to_dict(flat=False)
    return {k: normalize_query_param(v) for k, v in params_non_flat.items()}


def validate(
    body: Optional[Type[BaseModel]] = None,
    query: Optional[Type[BaseModel]] = None,
    form: Optional[Type[BaseModel]] = None,
    on_success_status: int = 200,
    exclude_none: bool = False,
    response_many: bool = False,
    request_body_many: bool = False,
    response_model: Optional[Type[BaseModel]] = None,
):
    """
    Decorator for route methods which will validate query and body parameters
    as well as serialize the response (if it derives from pydantic's BaseModel
    class).
    Request parameters are accessible via flask's `request` variable:
        - request.query_params
        - request.body_params
    `exclude_none` whether to remove None fields from response
    `response_many` whether content of response consists of many objects
        (e. g. List[BaseModel]). Resulting response will be an array of serialized
        models.
    `request_body_many` whether response body contains array of given model
        (request.body_params then contains list of models i. e. List[BaseModel])
    example:
    from flask import request
    from flask_pydantic import validate
    from pydantic import BaseModel
    class Query(BaseModel):
        query: str
    class Body(BaseModel):
        color: str
    class MyModel(BaseModel):
        id: int
        color: str
        description: str
    ...
    @app.route("/")
    @validate(query=Query, body=Body)
    def test_route():
        query = request.query_params.query
        color = request.body_params.query
        return MyModel(...)
    -> that will render JSON response with serialized MyModel instance
    """
    # TODO
    # Instead of relying on the global `request` and `current_user`
    # we should create a `ctx` variable which encapsulates both,
    # then inject that `ctx` into view functions.
    # This way we won't have global madness and our view functions will be
    # much more framework-agnostic.
    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            q, b, f, err = None, None, None, {}
            if query:
                query_params = normalize_query(request.args)
                try:
                    q = query(**query_params)
                except ValidationError as ve:
                    err["query_params"] = ve.errors()
            if body:
                body_params = request.get_json()
                if request_body_many:
                    try:
                        b = validate_many_models(body, body_params)
                    except ManyModelValidationError as e:
                        err["body_params"] = e.errors()
                else:
                    try:
                        b = body(**body_params)

                    except ValidationError as ve:
                        err["body_params"] = ve.errors()
            if form:
                form_params = request.form
                try:
                    f = form(**form_params)
                except ValidationError as ve:
                    err["form_params"] = ve.errors()

            # If we implement the TODO below, we won't need to do this
            # ugly monkeypatching
            request.query_params = q
            request.body_params = b
            request.form_params = f

            if err:
                res = ErrorSchema(error=err, code=400)
                return make_json_response(res, res.code)

            try:
                # TODO
                # Refactor ALL views to include a `ctx` argument
                # ctx should be a class with attributes such as
                # `sessions`: SessionRouter (`principal` == write_session for writes, `replicas` == [*read_replicas] for reads)
                # `current_user`: current_user
                # `request`: Request (inherit from Flask, add schema-parsed fields such as query_params, etc)
                res = func(*args, **kwargs)
            except HTTPError as http_err:
                res = ErrorSchema(error=http_err.message, code=http_err.code)
                return make_json_response(res, res.code)
            except SQLAlchemyError as db_err:
                db.session.rollback()
                res = ErrorSchema(error=db_err, code=500)
                return make_json_response(res, res.code)

            if response_model:
                return make_json_response(
                    res,
                    on_success_status,
                    exclude_none=exclude_none,
                    response_model=response_model,
                    many=isinstance(res, list),
                )

            if response_many:
                if is_iterable_of_models(res):
                    return make_json_response(
                        res,
                        on_success_status,
                        exclude_none=exclude_none,
                        many=True,
                        response_model=response_model,
                    )
                else:
                    raise InvalidIterableOfModelsException(res)

            if isinstance(res, BaseModel):
                return make_json_response(res, on_success_status, exclude_none=exclude_none)

            if isinstance(res, tuple) and len(res) == 2 and isinstance(res[0], BaseModel):
                return make_json_response(res[0], res[1], exclude_none=exclude_none)

            return res

        return wrapper

    return decorate