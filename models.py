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




# Users Model 
# This inherits from db.Model and UserMixin for Flask-Login integration.
class User(db.Model, UserMixin):
    """
    Represents a user in the application.

    Attributes:
        id (int): Unique identifier for the user.
        username (str): Unique username chosen by the user.
        email (str): User's email address.
        password_hash (str): Hashed password for authentication.
    """

    id = db.Column(db.Integer, primary_key=True) # Unique user ID
    username = db.Column(db.String(100), nullable=False, unique=True) # User's username
    email = db.Column(db.String(100), nullable=False, unique=True) # User's email
    password_hash = db.Column(db.Text(), nullable=False)  # Store hashed passwords

    # Relationship with Watchlist 
    watchlist_items = db.relationship("Watchlist", backref='user', lazy=True) # User's associated watchlist entries

    # Relationship with Review
    reviews = db.relationship('Review', back_populates='user')


    def __repr__(self):
        return f"<User {self.username}>"
    
    def set_password(self, password):
        """Hash the password and store it."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)





# Movie Model
# It inherits from db.model, which means it's a database model
class Movie(db.Model):
    """
    Represents a movie in the application.

    Attributes:
        id (int): Unique identifier for the movie.
        tmdb_id (int): Unique TMDb ID for identifying the movie.
        title (str): Title of the movie.
        release_date (str): Release date of the movie.
        overview (str): Overview or description of the movie.
        poster_path (str): URL path to the movie's poster image.
        genre_id (int): Foreign key referencing the genre of the movie.
        watchlist_items (list[Watchlist]): List of watchlist entries associated with the movie.
        reviews (list[Review]): List of reviews associated with the movie.
    """

    id = db.Column(db.Integer, primary_key=True)  # Unique ID for each movie
    tmdb_id = db.Column(db.Integer, unique=True, nullable=False) # Unique TMDb ID for identifying the movie
    title = db.Column(db.String(100), nullable=False)  # Title of the movie
    release_date = db.Column(db.String(50), nullable=True)  # Release date of the movie
    overview = db.Column(db.Text, nullable=True)  # Overview or description of the movie
    poster_path = db.Column(db.String(255), nullable=True)  # URL path to the movie's poster image
    genre_id = db.Column(db.Integer, db.ForeignKey('genre.id'), nullable=False)  # Foreign key to associate with Genre

   

    # Relationship with User (watchlist, ratings, reviews)
    # A movie can appear in multiple users' watchlists
    watchlist_items = db.relationship('Watchlist', backref='movie', lazy=True)  # Allows access to related watchlist items

    # Relationship with Review
    reviews = db.relationship('Review', back_populates='movie')

    def __repr__(self):
        return f"<Movie {self.title} ({self.release_date}) {self.poster_path}>" # String representation for debugging





# Genre Model
# it inherits from db.model, which means it's a database model
class Genre(db.Model):
    """
    Represents a genre of movies.

    Attributes:
        id (int): Unique identifier for the genre.
        name (str): Name of the genre.
        movies (list[Movie]): List of movies associated with this genre.
    """

    id = db.Column(db.Integer, primary_key=True)  # Unique ID for each genre
    name = db.Column(db.String, nullable=False, default="Unknown")  # Name of the genre with a default value

    # Relationship with Movie
    # A genre can have multiple associated movies.
    movies = db.relationship('Movie', backref='genre', lazy=True)  # Enables `genre.movies` to access all related movies

    
    def __repr__(self):
        return f"<Genre {self.name}>"





# TVShow Model
# it inherits from db.model, which means it's a database model
class TVShow(db.Model):
    """
    Represents a tv show

    Attributes:
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(255), nullable=False)
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)





# Watchlist Model to manage users' watchlists
# it inherits from db.model, which means it's a database model
class Watchlist(db.Model):
    """
    Represents an entry in a user's watchlist.

    Attributes:
        id (int): Unique identifier for the watchlist entry.
        user_id (int): Foreign key referencing the user.
        movie_id (int): Foreign key referencing the movie.
        added_on (datetime): Timestamp when the movie was added to the watchlist.
        status (str): Watch status (e.g., 'watching', 'completed').
    """

    id = db.Column(db.Integer, primary_key=True) # Unique ID for the entry
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Foreign Key to user
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False) # Foreign Key to movie
    added_on = db.Column(db.DateTime, default=datetime.utcnow) # When the movie was added to the watchlist
    status = db.Column(db.String(50), default="watching") # Watch status (e.g., 'watching', 'completed')


    def __repr__(self):
        return f"<Watchlist Movie ID {self.movie_id}, User ID {self.user_id}>"
    




# Watchlist Item Model
# it inherits from db.model, which means it's a database model
class WatchlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    media_type = db.Column(db.String(50), nullable=False)





# Review Model
class Review(db.Model):
    """
    Represents a review for a movie written by a user.

    Attributes:
        id (int): Unique identifier for the review.
        user_id (int): Foreign key referencing the user who wrote the review.
        movie_id (int): Foreign key referencing the movie being reviewed.
        rating (int): Rating given to the movie by the user.
        review_text (str): Textual content of the review.
        user (User): The user who wrote the review.
        movie (Movie): The movie that is being reviewed.
    """

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review_text = db.Column(db.Text, nullable=True)

    # Relationship with User
    user = db.relationship('User', back_populates='reviews')

    # Relationship with Movie
    movie = db.relationship('Movie', back_populates='reviews')










    

