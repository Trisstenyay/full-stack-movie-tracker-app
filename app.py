from flask import Flask, jsonify, render_template, request, redirect, url_for, flash # Import Flask core items
from flask_login import LoginManager, login_user, login_required, logout_user, current_user # Import Flask-Login components for user authentication and session management
import traceback
import requests # Import the requests library to make HTTP requests
from flask_sqlalchemy import SQLAlchemy # Import SQLAlchemy, an ORM (Object Relational Mapper) for database interactions
from models import db, connect_db # First, import db and connect_db
from models import User, Movie, Genre, Watchlist, Review # Import the models from the models.py file to use in the Flask app 
from forms import ReviewForm # Import the ReviewForm class from the forms module to handle form validation and submission
from datetime import datetime # Import Python's built-in datetime module to handle date and time
import os  # Import the os module to access environment variables
from dotenv import load_dotenv # This package loads variables from your .env file into your environment.

# Load variables from the .env file into the environment
load_dotenv()

app = Flask(__name__) # Initialize the Flask app Create an instance of the Flask class



app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('LOCAL_DATABASE_URL')

app.config['SECRET_KEY'] = "Capstone"  

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False # Disable SQLAlchemy's event system for performance reasons (optional but common practice)

# Initialize Flask-Login's LoginManager to handle user authentication
login_manager = LoginManager() # Create an instance of LoginManager to manage user sessions

# Configure the LoginManager to use the Flask app
login_manager.init_app(app) # Bind the LoginManager to the Flask application instance

login_manager.login_view = "login"  # Redirect to the 'login' route if the user is not authenticated

# Define a user loader function to retrieve the User object based on the user_id
@login_manager.user_loader
def load_user(user_id):
    """
    Given a user_id, return the corresponding User object.
    
    Flask-Login will call this function to load the user based on the user ID stored in the session.
    The user ID is typically stored as a session cookie, and this function fetches the User
    object from the database for each request.
    """
    return User.query.get(int(user_id))  # Convert user_id to int and query the User model to fetch the user



# Create tables in the database based on the models
with app.app_context():
    connect_db(app)
    # db.drop_all()      # ✅ Drop all tables (be careful: this deletes all data)
    # db.create_all()    # ✅ Recreate all tables with new schema




# Authentication headers and API_KEY = Bearer token
headers = {
    "accept": "application/json", # Specify the type of data we accept (JSON)
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIxMDkzODdhZGNkMTMyZGMzZTc4NzU2MWRmNzBlNjZiMyIsIm5iZiI6MTczNDYzMTk3OC4wMTQwMDAyLCJzdWIiOiI2NzY0NjIyYThkYzA0NmI5MTVhNGZjNDMiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.1Qp7p_YrH--rWMUizGo8ywOULxwoMebhZo5NBXXFiXk" # Added my API token
}





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
        # Render landing page for non-authenticated users
        return render_template("landing.html", user=current_user)



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



@app.route("/fetch_movies", methods=["GET"])
def fetch_movies():
    """
    Fetches movies from the TMDb API and stores them in the database.
    The API request retrieves a list of movies, and each movie is added to the database if it doesn't already exist.
    """
    api_url_movies = "https://api.themoviedb.org/3/movie/now_playing?language=en-US&page=1"

    try:
        response_movies = requests.get(api_url_movies, headers=headers)

        if response_movies.status_code == 200:
            data_movies = response_movies.json()
            movies = data_movies["results"]

            for m in movies:
                # Avoid adding duplicates
                existing_movie = Movie.query.filter_by(tmdb_id=m.get("id")).first()
                if not existing_movie:
                    genre_id = m["genre_ids"][0] if m.get("genre_ids") else None
                    genre = None
                    if genre_id:
                        genre = Genre.query.filter_by(id=genre_id).first()
                        if not genre:
                            genre = Genre(id=genre_id, name="Unknown")
                            db.session.add(genre)
                            db.session.commit()

                    movie = Movie(
                        tmdb_id=m.get("id"),
                        title=m.get("title", "Untitled"),
                        release_date=m.get("release_date"),
                        overview=m.get("overview", "No overview available"),
                        poster_path=m.get("poster_path"),
                        genre_id=genre.id if genre else None,
                        is_popular=False
                    )
                    db.session.add(movie)

            db.session.commit()

            return {"message": "Movies successfully fetched and saved."}, 200
        else:
            return {"error": "Failed to fetch movies from API."}, response_movies.status_code

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}, 500


@app.route("/fetch-movies")
def call_fetch_movies():
    return fetch_movies()


@app.route("/movies", methods=["GET"])
@login_required
def display_movies():
    """
    Displays all movies stored in the database (non-popular).
    If none exist yet, fetches them from TMDB first.
    """
    try:
        # If no non-popular movies exist, fetch them
        if Movie.query.filter_by(is_popular=False).count() == 0:
            fetch_movies()  # this inserts is_popular=False movies into the DB

        # Query non-popular movies
        movies = Movie.query.filter_by(is_popular=False).all()

        movie_list = [
            {
                "title": movie.title,
                "release_date": movie.release_date,
                "poster_path": movie.poster_path,
                "overview": movie.overview,
                "id": movie.id,
                "tmdb_id": movie.tmdb_id,
                "reviews": movie.reviews,
            }
            for movie in movies
        ]

        return render_template("movies.html", movies=movie_list, user=current_user)

    except Exception as e:
        print(f"Error fetching movies: {e}")
        return {"error": "An error occurred while retrieving movies."}, 500




@app.route("/genres", methods=["GET"])
def fetch_genres():
    """
    Fetches genres from the TMDb API and stores them in the database.
    Each genre fetched from the API is added to the database if it doesn't already exist.
    """
    api_url_genres = "https://api.themoviedb.org/3/genre/movie/list"

    try:
        response_genres = requests.get(api_url_genres, headers=headers)

        if response_genres.status_code == 200:
            data_genres = response_genres.json()
            genres = data_genres["genres"]

            for g in genres:
                existing_genre = Genre.query.filter_by(id=g["id"]).first()
                if not existing_genre:
                    genre = Genre(id=g["id"], name=g["name"])
                    db.session.add(genre)
                else:
                    existing_genre.name = g["name"]

            db.session.commit()

            return {"message": "Genres fetched and stored successfully."}, 200
        else:
            return {"error": "Failed to fetch genres from the API."}, 500

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return {"error": "An error occurred while connecting to the API."}, 500



@app.route("/display_genres", methods=["GET"])
def display_genres():
    """
    Displays all genres stored in the database. Retrieves the genres and renders them in the template.
    """
    try:
        genres = Genre.query.all()

        genre_list = [{"id": genre.id, "name": genre.name} for genre in genres]

        return render_template("genres.html", genres=genre_list, user=current_user)

    except Exception as e:
        print(f"Error fetching genres: {e}")
        return {"error": "An error occurred while retrieving genres."}, 500



@app.route("/search", methods=["GET"])
@login_required
def search():
    """
    Search for movies based on the query.
    Returns a list of movie dicts like in /movies for consistency.
    """
    query = request.args.get("query", "")
    
    if not query:
        return render_template("search.html", results=[], query=query, user=current_user)

    search_pattern = f"%{query}%"
    matched_movies = db.session.execute(
        db.select(Movie).filter(Movie.title.ilike(search_pattern))
    ).scalars().all()

    results = [
        {
            "title": movie.title,
            "release_date": movie.release_date,
            "poster_path": movie.poster_path,
            "overview": movie.overview,
            "id": movie.id,
            "reviews": movie.reviews
        }
        for movie in matched_movies
    ]

    return render_template("search.html", results=results, query=query, user=current_user)



def fetch_popular_movies():
    url = "https://api.themoviedb.org/3/movie/popular?language=en-US&page=1"
    response = requests.get(url, headers=headers)
    data = response.json()
    return data.get("results", [])



@app.route("/popular")
@login_required
def show_popular_movies():
    """Fetch and store popular movies from TMDB, then show only is_popular=True."""
    url = "https://api.themoviedb.org/3/movie/popular"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        movies = data.get("results", [])

        for m in movies:
            tmdb_id = m.get("id")

            # Check if this movie already exists in the DB
            existing = Movie.query.filter_by(tmdb_id=tmdb_id).first()
            if not existing:
                movie = Movie(
                    tmdb_id=tmdb_id,
                    title=m.get("title", "Untitled"),
                    release_date=m.get("release_date"),
                    overview=m.get("overview", "No overview available"),
                    poster_path=m.get("poster_path"),
                    is_popular=True
                )
                db.session.add(movie)

        db.session.commit()

    # Now show only movies marked as popular
    popular_movies = Movie.query.filter_by(is_popular=True).all()
    return render_template("popular.html", movies=popular_movies, user=current_user)



@app.route("/add_to_watchlist", methods=["POST"])
@login_required
def add_to_watchlist():
    # 1. Grab and validate tmdb_id
    tmdb_id = request.form.get("tmdb_id")
    if not tmdb_id or not tmdb_id.isdigit():
        flash("Invalid movie ID. Please try again.", "danger")
        return redirect(url_for("watchlist"))

    tmdb_id = int(tmdb_id)

    # 2. Grab all other fields from the form
    title = request.form.get("title")
    poster_path = request.form.get("poster_path")
    overview = request.form.get("overview")
    release_date = request.form.get("release_date")
    status = request.form.get("status")

    # 3. Check if the movie already exists in the database
    movie = Movie.query.filter_by(tmdb_id=tmdb_id).first()

    # 4. If not in the DB yet, create and add it
    if not movie:
        movie = Movie(
            tmdb_id=tmdb_id,
            title=title,
            poster_path=poster_path,
            overview=overview,
            release_date=release_date,
            is_popular=request.referrer and "/popular" in request.referrer
        )
        db.session.add(movie)
        db.session.commit()

    # 5. Check if it's already in the user's watchlist
    existing = Watchlist.query.filter_by(user_id=current_user.id, movie_id=movie.id).first()
    if existing:
        flash("Movie is already in your watchlist.", "info")
    else:
        watchlist_item = Watchlist(
            user_id=current_user.id,
            movie_id=movie.id,
            status=status
        )
        db.session.add(watchlist_item)
        db.session.commit()
        flash(f"{title} added to your watchlist!", "success")

    return redirect(url_for("watchlist"))




@app.route("/watchlist")
@login_required
def watchlist():
    try:
        # Get all Watchlist entries for the current user
        watchlist_items = Watchlist.query.filter_by(user_id=current_user.id).all()

        # Get associated Movie objects using the relationship you added
        movies = [item.movie for item in watchlist_items]

        return render_template("watchlist.html", movies=movies, user=current_user)

    except Exception as e:
        print("⚠️ WATCHLIST ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500 



@app.route("/update_status/<int:movie_id>", methods=["POST"])
@login_required
def update_status(movie_id):
    try:
        new_status = request.form.get("status")
        watchlist_item = Watchlist.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()

        if not watchlist_item:
            flash("Movie not found in your watchlist.", "danger")
            return redirect(url_for("watchlist"))

        watchlist_item.status = new_status
        db.session.commit()
        flash("Status updated successfully!", "success")
    except Exception as e:
        print(f"Error updating status: {e}")
        flash("Error updating status.", "danger")

    return redirect(url_for("watchlist"))



@app.route("/remove_from_watchlist/<int:movie_id>", methods=["POST"])
def remove_from_watchlist(movie_id):
    """
    Removes a movie from the user's watchlist.
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

    return redirect(url_for('watchlist'))



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



@app.route('/review/<int:review_id>/delete', methods=['POST'])
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

