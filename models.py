from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


# Initialize the database instance here
db = SQLAlchemy()

def connect_db(app):
    """Connect this database to provided Flask app. You should call this in your Flask app.
    """

    db.app = app
    db.init_app(app)



### ----------------------------
### USER MODEL
### ----------------------------

class User(db.Model, UserMixin):
    """Represents a user in the application."""
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)

    # Backref comes from Review and Watchlist
    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


### ----------------------------
### MOVIE MODEL
### ----------------------------

class Movie(db.Model):
    """Represents a movie."""
    __tablename__ = "movie"

    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    release_date = db.Column(db.String(50), nullable=True)
    overview = db.Column(db.Text, nullable=True)
    poster_path = db.Column(db.String(255), nullable=True)
    genre_id = db.Column(db.Integer, db.ForeignKey('genre.id'), nullable=True)
    is_popular = db.Column(db.Boolean, nullable=False, default=False)
    

    # Backrefs from Review and Watchlist

    def __repr__(self):
        return f"<Movie {self.title} ({self.release_date})>"


### ----------------------------
### GENRE MODEL
### ----------------------------

class Genre(db.Model):
    """Represents a genre of movies."""
    __tablename__ = "genre"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, default="Unknown")

    # genre.movies will work thanks to backref
    movies = db.relationship('Movie', backref='genre', lazy=True)

    def __repr__(self):
        return f"<Genre {self.name}>"


### ----------------------------
### WATCHLIST MODEL
### ----------------------------

class Watchlist(db.Model):
    """Manages users' watchlists."""
    __tablename__ = "watchlist"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    added_on = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="watching")

    # These backrefs will auto-create:
    # - user.watchlist_items
    # - movie.watchlist_items
    user = db.relationship("User", backref="watchlist_items")
    movie = db.relationship("Movie", backref="watchlist_items")

    def __repr__(self):
        return f"<Watchlist Movie ID {self.movie_id}, User ID {self.user_id}>"


### ----------------------------
### REVIEW MODEL
### ----------------------------

class Review(db.Model):
    """Represents a review written by a user."""
    __tablename__ = "review"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review_text = db.Column(db.Text, nullable=True)

    # These backrefs will auto-create:
    # - user.reviews
    # - movie.reviews
    user = db.relationship('User', backref='reviews')
    movie = db.relationship('Movie', backref='reviews')

    def __repr__(self):
        return f"<Review by User {self.user_id} for Movie {self.movie_id}>"