from app import api
from app.users.manager import UserManager
from flask import jsonify
from flask_restful import Resource, reqparse

post_parser = reqparse.RequestParser()
post_parser.add_argument('email', required=True, type=str)
post_parser.add_argument('password', required=True, type=str)
post_parser.add_argument('confirmedPassword', required=True, type=str)
post_parser.add_argument('firstName', required=True, type=str)
post_parser.add_argument('lastName', required=True, type=str)

def init(app, api, database):
    user_manager = UserManager()

    class User(Resource):

        def post(self):
            args = post_parser.parse_args()

            # TODO: figure out how to properly throw errors
            if args.password != args.confirmedPassword:
                return jsonify({
                    "error": "This would say that password and confirmedPassword are not equivalent"
                })

            existing_user = user_manager.find_by_email(args.email)
            print(existing_user)
            if existing_user:
                return jsonify({
                    "error": "This would say that a user with that email already exists"
                })

            # TODO: marshal the data
            res = user_manager.create(args)
            return jsonify(res.to_dict())

    api.add_resource(User, '/users')
