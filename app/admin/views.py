"""
This module abstracts user functions and separates them from normal tipster actions such as those
in the main blueprint
"""
from flask import request, make_response, jsonify
import jwt
import datetime as dt
from werkzeug.security import check_password_hash
from flask_restful import Resource, Api
from . import user
from ..models import Tipster, Users, UsersSchema
from manage import app
from functools import wraps

tipster = Tipster()
api = Api(user)
userschema = UsersSchema(many=True)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        """
        returns an instance of the user class else returns a None object if the user is not found
        """
        token = False
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        if not token:
            return {'message': 'Token is missing'}
        try:
            key = app.config['SECRET_KEY']
            data = jwt.decode(token, key)
            user = Users.query.filter_by(id=data['user_id']).first()
            if user is None:
                raise Exception('user is None')
        except:
            return {'message': 'Token is invalid'}
        return f(user, *args, **kwargs)
    return decorated


def admin_eyes(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        """
        returns an instance of the user class else returns a None object if the user is not found
        """
        token = False
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        if not token:
            return {'message': 'Token is missing'}
        try:
            key = app.config['SECRET_KEY']
            data = jwt.decode(token, key)
            user = Users.query.filter_by(id=data['user_id']).first()
            if user is None:
                raise Exception('user is None')
        except:
            return {'message': 'Token is invalid'}
        if user.admin:
            return f(*args, **kwargs)
        return {'message': 'Method is not allowed'}
    return decorated


def login_failed():
    return make_response('could not verify', 401, {
                'WWW-Authenticate' : 'Basic realm="Login required"'
            })


class User(Resource):
    """
    Functions:
    -> Register: -> post details to create an account
    -> login -> post account login credentials to have access to a security token
    -> edit -> to update a user's profile(put operations)
    -> admin tasks:
        -> get a list of all users
        -> delete users
        -> promote users to admin
    """


class Register(User):
    """supports methods for registering users, deleting accounts"""
    def post(self):
        """
        creating a new user account instance
                    INPUT
        "name": "<name>",
        "email": "<email>",
        "user_name": "<user_name>",
        "password": "<password>"
        """
        data = request.get_json()
        try:
            yes = tipster.add_sharp(data)
        except KeyError:
            return {'message': 'error with the keys', 'sample':
                {
                    "name": "<name>",
                    "email": "<email>",
                    "user_name": "<user_name>",
                    "password": "<password>"
                }}
        if yes:
            return {'message': 'successfully added',
                    'url': ''
            }



class Many(User):
    """ supports get only-> returns a list of all the users and their details"""
    @token_required
    @admin_eyes
    def get(self, current_user):
        """classified admin eyes only
        returns a list of all the users in the system"""
        # if not current_user.admin:
        #     return {'message': 'Method not allowed'}, 503
        users = Users.query.all()
        semi_list = list()
        for user in users:
            semi_list.append(user)

        response = userschema.dump(semi_list)
        diction_data = response.data
        return {'users': diction_data}

api.add_resource(Many, '/')


class Single(User):
    """ Returns a single instance of a user"""
    @token_required
    def get(self, current_user, user_id):
        """classified owner's eyes only"""
        if current_user.id != user_id:
            # check that the logged in user is the same as the one authenticated
            return {'message': 'Method not allowed'}, 503
        user = Users.query.filter_by(id=user_id).first()
        if not user:
            return {'message': 'user not found'}, 404
        userschema = UsersSchema()
        schemaobject = userschema.dump(user)
        return {'users': schemaobject.data}


api.add_resource(Single, '/<int:user_id>')

class Login(User):
    """authenticate a person and return a token for future authentications
    input: an accounts credentials: username and Password
    output: a serialized token string"""
    def post(self):
        auth = request.authorization

        if not auth or not auth.username or not auth.password:
            login_failed()
        user = Users.query.filter_by(user_name=auth.username).first()
        if not user:
            login_failed()
        if check_password_hash(user.password, auth.password):
            token = jwt.encode({'user_id': user.id, 'exp': dt.datetime.utcnow() + dt.timedelta(hours=1)}, app.config['SECRET_KEY'])
            return jsonify({'token': token.decode("UTF-8")})
        return login_failed()


class RERegister(User):
    @token_required
    def put(self, user, user_id):
        """Modification of an existing account instance by the account owner"""
        current_user = Users.query.filter_by(id=user_id).first()
        if user.admin:
            # means we are promoting user
            if not current_user.admin:
                current_user.admin = True
                return {'message': 'user succesfully modified',
                    'url': '',
                    'user_details': ''
                    }
            else:
                current_user.admin = False
                return {'message': 'user succesfully modified',
                    'url': '',
                    'user_details': ''
                    }
        if user.id != current_user.id:
            return {'message': 'Method not allowed'}
        data = request.get_json()
        # we know just modify the new information
        response = tipster.modify_sharp(data)
        if response:
            return {'message': 'user succesfully modified',
                    'url': '',
                    'user_details': ''
                    }
        else:
            return {'message': 'ERROR: user not modified'}

    @admin_eyes
    def delete(self, user, user_id):
        """admin_eyes and accounts owner eyes only"""
        current_user = Users.query.filter_by(id=user_id).first()
        if user.id != current_user.id or not user.admin:
            return {'message': 'Method not allowed'}
        done = tipster.delete_sharp(user)
        if done:
            return {'message': 'user deleted'}
        else:
            return {'message': 'user not deleted'}


api.add_resource(Register, '/register')
api.add_resource(RERegister, '/<int:user_id>')
api.add_resource(Login, '/login')

