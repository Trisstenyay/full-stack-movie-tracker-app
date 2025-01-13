from flask import Flask, render_template, request, redirect, url_for, flash # Import Flask core items
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import requests # Import the requests library to make HTTP requests
from flask_sqlalchemy import SQLAlchemy # Import SQLAlchemy, an ORM (Object Relational Mapper) for database interactions
from models import db, connect_db, User, Movie, Genre, TVShow, Watchlist, Watchlist, Review # Import the models from the models.py file to use in the Flask app
from forms import ReviewForm
from datetime import datetime # Import Python's built-in datetime module to handle date and time
import os  # Import the os module to access environment variables

app = Flask(__name__) # Initialize the Flask app Create an instance of the Flask class

# Use the DATABASE_URL environment variable for the database URI
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "postgresql://trisstenyay:Dreamchaser4ever@localhost/movie_app_db")  # Fallback to default if not set
app.config['SECRET_KEY'] = "Capstone"  # Secret key = "Capstone"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False # Tell flask not to track database modifications, saving resources
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Replace with your login route name

@login_manager.user_loader
def load_user(user_id):
    """Given *user_id*, return the associated User object."""
    return User.query.get(int(user_id))


# Create tables in the database based on the models defined in models.py
with app.app_context():
    connect_db(app)
    # db.metadata.clear()
    # db.drop_all()
    db.create_all()  # Ensures the table(s) are created in the database



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





@app.route("/fetch_movies", methods=["GET"])
def fetch_movies():
    """
    Fetches movies from the TMDb API and stores them in the database.
    The API request retrieves a list of movies, and each movie is added to the database if it doesn't already exist.
    """
    api_url_movies = "https://api.themoviedb.org/3/discover/movie"

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
                        genre_id=genre.id if genre else None
                    )
                    db.session.add(movie)

            db.session.commit()

            return {"message": "Movies successfully fetched and saved."}, 200
        else:
            return {"error": "Failed to fetch movies from API."}, response_movies.status_code

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}, 500





@app.route("/movies", methods=["GET"])
def display_movies():
    """
    Displays all movies stored in the database. Retrieves the list of movies and passes them to the template.
    """
    try:
        movies = Movie.query.all()

        movie_list = [
            {
                "title": movie.title,
                "release_date": movie.release_date,
                "poster_path": movie.poster_path,
                "overview": movie.overview,
                "id": movie.id,
                "reviews": movie.reviews
            }
            for movie in movies
        ]

        return render_template('movies.html', movies=movie_list, user=current_user)

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

