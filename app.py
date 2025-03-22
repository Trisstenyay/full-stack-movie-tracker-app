from flask import Flask, json, jsonify, render_template, request, redirect, url_for, flash # Import Flask core items
from flask_login import LoginManager, login_user, login_required, logout_user, current_user # Import Flask-Login components for user authentication and session management
import requests # Import the requests library to make HTTP requests
from flask_sqlalchemy import SQLAlchemy # Import SQLAlchemy, an ORM (Object Relational Mapper) for database interactions
from models import db, connect_db # First, import db and connect_db
from models import User, Movie, Genre, TVShow, Watchlist, Review # Import the models from the models.py file to use in the Flask app 
from forms import ReviewForm # Import the ReviewForm class from the forms module to handle form validation and submission
from datetime import datetime # Import Python's built-in datetime module to handle date and time
import os  # Import the os module to access environment variables
from dotenv import load_dotenv # This package loads variables from your .env file into your environment.
from sqlalchemy import text

# Step 1: Initialize Flask app
app = Flask(__name__)  # Initialize the Flask app

# Step 2: Load environment variables from the .env file
load_dotenv()

# Step 3: Set up the database URI and other configurations
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('FLASK_DATABASE_URI', os.getenv('LOCAL_DATABASE_URL'))
app.config['SECRET_KEY'] = "Capstone"  # Secret key
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # Disable modification tracking

# Step 4: ✅ Connect the database (from models.py where `db` is initialized)
connect_db(app)  # This automatically calls db.init_app(app)

# Step 5: Get the Bearer token from the .env file
TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN")

# Step 6: Get the API key from .env
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Step 7: Set up and initialize Flask-Login
login_manager = LoginManager()  # Create an instance of LoginManager
login_manager.init_app(app)  # Bind LoginManager to the Flask app
login_manager.login_view = "login"  # Redirect to the 'login' route if the user isn't authenticated

# Step 8: Define a user loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """Return the User object based on user_id stored in the session."""
    return User.query.get(int(user_id))  # Query the User model

# Step 9: Setup API headers for external requests (e.g., TMDB)
headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {TMDB_BEARER_TOKEN}"
}

# Step 10: Create tables manually based on the models (using app context)
with app.app_context():
    # db.drop_all()
    # db.create_all()  # Create tables in the database based on the models
    # print("Tables created successfully!")
     pass

if __name__ == "__main__":
    app.run(debug=True)  # Run the Flask app in debug mode




@app.route("/")
def home():
    """
    Home route, checks if the user is authenticated and renders the home page accordingly.
    If the user is authenticated, it fetches user-specific data.
    """
    if current_user.is_authenticated:
        # Fetch user-specific data if logged in
        return render_template("home.html", user=current_user)
    else:
        # Render home page for non-authenticated users
        return render_template("home.html", user=current_user)





@app.route("/signup", methods=["GET", "POST"])
def signup():
    """
    Sign up route. Handles both GET (rendering the signup form) and POST (processing form data)
    requests. The POST request checks if the username or email already exists in the database.
    If not, it creates a new user and redirects to the login page.
    """
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        # Check if the username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("Username or email already exists.", "danger")
            return redirect(url_for("signup"))

        new_user = User(username=username, email=email)
        new_user.set_password(password)  # Hash the password before saving
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")





@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login route. If the user is already authenticated, redirects them to the home page.
    On POST, the function checks the provided credentials and logs the user in if valid.
    """
    if current_user.is_authenticated:
        return redirect(url_for('home'))  # Redirect to home if already logged in

    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):  # Check if password matches
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('home'))  # Redirect to home after successful login
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")





@app.route("/logout")
@login_required
def logout():
    """
    Logout route. Logs the current user out and redirects to the home page with a message.
    """
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))





@app.route("/profile")
@login_required
def profile():
    """
    Profile route. Renders the profile page with the current user's details.
    """
    return render_template("profile.html", user=current_user)





MOVIE_API_URL = "https://api.themoviedb.org/3/discover/movie"

@app.route("/fetch_movies", methods=["GET"])
def fetch_movies():
    """
    Fetches movies from The Movie Database (TMDb) API and stores them in the database.
    Avoids inserting duplicates and ensures every movie has a valid overview.
    """
    tmdb_api_key = os.getenv("TMDB_API_KEY")  # Load API key from environment variables

    url = f"{MOVIE_API_URL}?api_key={tmdb_api_key}"  # Construct API request URL
    response = requests.get(url)  # Send GET request to TMDb API

    if response.status_code == 200:  # Check if the request was successful
        movie_data = response.json().get('results', [])  # Extract movie results from API response
        
        print("Fetched movies:", json.dumps(movie_data, indent=4))  # Log fetched movies for debugging

        tmdb_ids = []  # List to track inserted movie IDs

        for movie in movie_data:
            tmdb_id = movie.get("id")  # Get the unique TMDb movie ID

            # Check if the movie already exists in the database
            if not Movie.query.filter_by(tmdb_id=tmdb_id).first():
                genre_ids = movie.get("genre_ids", [])  # Get list of genre IDs
                movie_genres = []  # Store Genre objects

                # Handle missing overview by setting a default value
                if not movie.get("overview"):
                    movie["overview"] = "No description available."

                # Find and associate genres with the movie
                for genre_id in genre_ids:
                    genre = Genre.query.filter_by(id=genre_id).first()
                    if genre:
                        movie_genres.append(genre)

                # Create a new Movie object with the fetched details
                new_movie = Movie(
                    tmdb_id=tmdb_id,
                    title=movie.get("title"),
                    release_date=movie.get("release_date"),
                    overview=movie.get("overview"),
                    poster_path=movie.get("poster_path"),
                    genre_id=movie_genres[0].id if movie_genres else None  # Assign first genre if available
                )

                db.session.add(new_movie)  # Add new movie to session
                db.session.commit()  # Commit the movie to the database

                tmdb_ids.append(tmdb_id)  # Keep track of inserted movie IDs
                
                # Log the inserted movie and its overview
                print(f"Movie: {movie['title']} - Overview: {movie['overview']}")

        return jsonify({"message": "Movies fetched and stored successfully!"})

    # Handle API request failure
    return jsonify({"error": "Failed to fetch movies", "details": response.text}), 500

    



@app.route("/movies", methods=["GET"])
def display_movies():
    """
    Fetches all movies stored in the database and passes them to the template.
    Ensures movies are retrieved correctly and handles missing overviews.
    """
    try:
        # Fetch all movies from the database
        movies = Movie.query.all()

        # Log the total number of movies found for debugging
        print(f"Total Movies Found: {len(movies)}")

        # Construct a list of movie dictionaries for rendering in the template
        movie_list = [
            {
                "id": movie.id,
                "title": movie.title,
                "release_date": movie.release_date,
                "poster_path": movie.poster_path,
                "overview": movie.overview if movie.overview else "No description available.",  # Handle missing overviews
                "reviews": movie.reviews  # Assuming this is a relationship or field
            }
            for movie in movies
        ]

        # Render the movies.html template and pass the movie data along with the current user
        return render_template("movies.html", movies=movie_list, user=current_user)

    except Exception as e:
        # Log any errors that occur during movie retrieval
        print(f"Error fetching movies: {e}")
        return jsonify({"error": "An error occurred while retrieving movies."}), 500





@app.route("/genres", methods=["GET"])
def fetch_genres():
    """
    Fetches genres from the TMDb API and stores them in the database.
    Each genre fetched from the API is added to the database if it doesn't already exist.
    """
    api_url_genres = "https://api.themoviedb.org/3/genre/movie/list"
    headers = {"Authorization": "Bearer " + TMDB_BEARER_TOKEN}

    try:
        # Send a GET request to the TMDb API to fetch genres
        response_genres = requests.get(api_url_genres, headers=headers)

        if response_genres.status_code == 200:
            # If the response is successful, process the genres
            data_genres = response_genres.json()  # Parse the JSON response
            genres = data_genres["genres"]  # Extract the genres list

            for g in genres:
                # Check if the genre is already in the database
                existing_genre = Genre.query.filter_by(id=g["id"]).first()
                if not existing_genre:
                    # If the genre doesn't exist, add it to the database
                    genre = Genre(id=g["id"], name=g["name"])
                    db.session.add(genre)
                else:
                    # If the genre exists, update the name
                    existing_genre.name = g["name"]

            db.session.commit()  # Commit the changes to the database

            # Return a success message
            return {"message": "Genres fetched and stored successfully."}, 200
        else:
            # If the API request fails, return an error message
            return {"error": "Failed to fetch genres from the API."}, 500

    except requests.exceptions.RequestException as e:
        # Handle any errors with the API request
        print(f"Request failed: {e}")
        return {"error": "An error occurred while connecting to the API."}, 500

if __name__ == "__main__":
    app.run(debug=True)  # Run the app with debugging enabled





@app.route("/search", methods=["GET", "POST"])
def search():
    """
    Search for movies or TV shows based on the provided query and media type.
    The query parameter is used for searching, and media_type determines whether to search for a movie or TV show.
    """
    query = request.args.get("query", "")
    media_type = request.args.get("type", "movie")

    if not query:
        return render_template("search.html", results=[], query=query, user=current_user)

    search_pattern = f"%{query}%"
    results = []

    if media_type == "movie":
        results = db.session.execute(
            db.select(Movie).filter(Movie.title.ilike(search_pattern))
        ).scalars().all()

    elif media_type == "tv":
        results = db.session.execute(
            db.select(TVShow).filter(TVShow.title.ilike(search_pattern))
        ).scalars().all()

    return render_template("search.html", results=results, query=query, user=current_user)





@app.route("/add_to_watchlist", methods=["POST"])
def add_to_watchlist():
    """
    Adds a movie or TV show to the watchlist. The media_id, title, media_type, and status are taken from the form,
    and the item is added to the Watchlist table in the database.
    """
    if request.method == "POST":
        media_id = request.form.get("media_id")
        title = request.form.get("title")
        media_type = request.form.get("media_type")
        status = request.form.get("status")

        if not media_id or not title or not media_type or not status:
            missing_fields = []
            if not media_id:
                missing_fields.append('Media ID')
            if not title:
                missing_fields.append('Title')
            if not media_type:
                missing_fields.append('Media Type')
            if not status:
                missing_fields.append('Status')
            missing_fields_str = ', '.join(missing_fields)
            return f"<h1>Missing required information: {missing_fields_str}</h1>", 400

        watchlist_item = Watchlist(
            user_id=current_user.id,
            movie_id=media_id,
            status=status
        )

        db.session.add(watchlist_item)
        db.session.commit()

        flash("Added to your watchlist.", "success")
        return redirect(url_for('home'))





@app.route("/watchlist", methods=["GET"])
def display_watchlist():
    """
    Displays all movies in the user's watchlist. Retrieves movies based on the watchlist and renders them in the template.
    """
    try:
        watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
        movie_ids = [w.movie_id for w in watchlist]
        movies = Movie.query.filter(Movie.id.in_(movie_ids)).all()

        return render_template('watchlist.html', movies=movies, user=current_user)

    except Exception as e:
        print(f"Error fetching movies: {e}")
        return {"error": "An error occurred while retrieving movies."}, 500
    
        return redirect(url_for('home'))





@app.route("/remove_from_watchlist/<int:movie_id>", methods=["POST"])
def remove_from_watchlist(movie_id):
    """
    Removes a movie or TV show from the user's watchlist.
    """
    try:
        # Find the watchlist item for the current user and movie
        watchlist_item = Watchlist.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()

        if watchlist_item:
            db.session.delete(watchlist_item)
            db.session.commit()
            flash("Movie removed from your watchlist.", "success")
        else:
            flash("Movie not found in your watchlist.", "danger")

    except Exception as e:
        print(f"Error removing movie from watchlist: {e}")
        flash("An error occurred while removing the movie.", "danger")

    return redirect(url_for('display_watchlist'))





@app.route('/movies/<int:movie_id>/review', methods=['GET', 'POST'])
def review_movie(movie_id):
    """
    Allows the user to submit a review for a specific movie. The review form includes a rating and review text.
    The review is added to the database and associated with the movie and user.
    """
    form = ReviewForm()
    movie = Movie.query.get_or_404(movie_id)

    if form.validate_on_submit():
        review = Review(
            user_id=current_user.id,
            movie_id=movie.id,
            rating=form.rating.data,
            review_text=form.review_text.data
        )
        db.session.add(review)
        db.session.commit()
        flash('Your review has been submitted.', 'success')
        return redirect(url_for('review_movie', movie_id=movie.id)) # Redirect to view the updated reviews
    
    # Fetch all reviews for the movie
    reviews = Review.query.filter_by(movie_id=movie.id).all()

    return render_template('review_movie.html', form=form, movie=movie, reviews=reviews)





@app.route('/review/<int:review_id>/delete', methods=['GET'])
@login_required
def delete_review(review_id):
    """
    Deletes a specific review by the user. Only the user who created the review can delete it.
    """
    review = Review.query.get_or_404(review_id)
    if review.user_id != current_user.id:
        flash('You do not have permission to delete this review.', 'danger')
        return redirect(url_for('review_movie', movie_id=review.movie_id))
    
    db.session.delete(review)
    db.session.commit()
    flash('Your review has been deleted.', 'success')
    return redirect(url_for('review_movie', movie_id=review.movie_id))

