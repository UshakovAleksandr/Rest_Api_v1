from flask import Flask
from flask_restful import Api, Resource, reqparse
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

app = Flask(__name__)
api = Api(app)
base_dir = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(base_dir, 'app_main.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db, render_as_batch=True)


class AuthorModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True)
    surname = db.Column(db.String(32), unique=True)
    quotes = db.relationship('QuoteModel', backref='author', lazy='joined', cascade="all, delete-orphan")

    def __init__(self, name, surname):
        self.name = name
        self.surname = surname

    def to_dict(self):
        d = {}
        for column in self.__table__.columns:
            d[column.name] = str(getattr(self, column.name))
        return d


class QuoteModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey(AuthorModel.id))
    quote = db.Column(db.String(255), unique=False)

    def __init__(self, author, quote):
        self.author_id = author.id
        self.quote = quote

    def to_dict(self):
        d = {}
        for column in self.__table__.columns:
            d[column.name] = str(getattr(self, column.name))
        d["author"] = self.author.to_dict()
        return d


class Author(Resource):

    def get(self, id=None):
        if id is None:
            authors = AuthorModel.query.all()
            if not authors:
                return "There is no author yet", 200
        else:
            author = AuthorModel.query.get(id)
            if not author:
                return f"No author with id={id}", 404
            authors = [author]
        authors_lst = [author.to_dict() for author in authors]

        return authors_lst, 200

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("name", required=True)
        parser.add_argument("surname", required=True)
        author_data = parser.parse_args()

        author = AuthorModel.query.filter(AuthorModel.name == author_data["name"],
                                          AuthorModel.surname == author_data["surname"]).all()
        if author:
            if author[0].name == author_data["name"] or author[0].surname == author_data["surname"]:
                return "An author with such name or surname already exists. " \
                       "You can only add a unique name and surname", 400

        author = AuthorModel(author_data["name"], author_data["surname"])

        try:
            db.session.add(author)
            db.session.commit()
            return author.to_dict(), 201
        except:
            return "An error occurred while adding new author" \
                   "or an author with such name or surname already exists. " \
                    "You can only add a unique name and surname", 404

    def put(self, id):
        author = AuthorModel.query.get(id)
        if not author:
            return f"No author with id={id}", 404
        parser = reqparse.RequestParser()
        parser.add_argument("name")
        parser.add_argument("surname")
        author_data = parser.parse_args()

        if author.name == author_data["name"] and author.surname == author_data["surname"]:
            return "The name and surname of the author you want to change" \
                   " matches the ones you pass in the request." \
                   " Enter another name or surname of the author." \
                   " The changes will not be applied.", 400

        author.name = author_data["name"] or author.name
        author.surname = author_data["surname"] or author.surname

        try:
            db.session.add(author)
            db.session.commit()
            return author.to_dict(), 200
        except:
            return "An error occurred while changing the author", 404

    def delete(self, id):
        author = AuthorModel.query.get(id)
        if not author:
            return f"No author with id={id}", 404
        try:
            db.session.delete(author)
            db.session.commit()
            return f"Author with id={id} deleted", 200
        except:
            return "An error occurred while deleting the author", 404


class Quotes(Resource):

    def get(self, author_id=None, quote_id=None):
        if author_id is None and quote_id is None:
            quotes = QuoteModel.query.all()
            if not quotes:
                return "There are no quotes yet", 200

        if author_id is not None and quote_id is None:
            quotes = QuoteModel.query.filter(QuoteModel.author_id == author_id).all()
            if not quotes:
                return f"Author with id={author_id} has no quotes or author is not exists", 404

        if author_id is not None and quote_id is not None:
            quote = QuoteModel.query.filter(QuoteModel.author_id == author_id, QuoteModel.id == quote_id).all()
            if not quote:
                return f"Author with id={author_id} has no quote with id={quote_id} or author is not exists", 404
            quotes = quote

        quotes_lst = [quote.to_dict() for quote in quotes]
        return quotes_lst, 200

    def post(self, author_id):
        parser = reqparse.RequestParser()
        parser.add_argument("quote")
        quote_data = parser.parse_args()

        author = AuthorModel.query.get(author_id)
        quote = QuoteModel(author, quote_data["quote"])
        db.session.add(quote)
        db.session.commit()

        return quote.to_dict(), 200

    def put(self, author_id, quote_id):
        quote = QuoteModel.query.filter(QuoteModel.author_id == author_id, QuoteModel.id == quote_id).all()
        if not quote:
            return f"This author has no quote with id={quote_id}", 404
        parser = reqparse.RequestParser()
        parser.add_argument("quote")
        quote_data = parser.parse_args()

        quote[0].quote = quote_data["quote"] or quote[0].quote

        db.session.add(quote[0])
        db.session.commit()
        return quote[0].to_dict(), 200

    def delete(self, author_id, quote_id):

        quote = QuoteModel.query.filter(QuoteModel.author_id == author_id, QuoteModel.id == quote_id).all()
        if not quote:
            return f"No quote with id={quote_id}", 404

        db.session.delete(quote[0])
        db.session.commit()

        return f"Quote with id={quote_id} deleted", 200


api.add_resource(Author, "/authors", "/authors/<int:id>")
api.add_resource(Quotes, "/quotes", "/authors/<int:author_id>/quotes",
                                    "/authors/<int:author_id>/quotes/<int:quote_id>")


if __name__ == '__main__':
    app.run(debug=True)
