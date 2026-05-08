#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from forms import *
from datetime import datetime

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Import models after db is initialized to avoid circular imports
from models import Venue, Artist, Show, Genre

#----------------------------------------------------------------------------#
# Helpers
#----------------------------------------------------------------------------#

def get_or_create_genres(genre_names):
    """
    Return Genre ORM objects for each name, inserting any that do not yet exist.

    SQL equivalent:
        SELECT id FROM "Genre" WHERE name = :name;
        INSERT INTO "Genre" (name) VALUES (:name);   -- only when not found
    """
    result = []
    for name in genre_names:
        genre = Genre.query.filter_by(name=name).first()
        if not genre:
            genre = Genre(name=name)
            db.session.add(genre)
        result.append(genre)
    return result

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    if isinstance(value, str):
        date = dateutil.parser.parse(value)
    else:
        date = value
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
    # SQL equivalent:
    #   SELECT id, name, city, state FROM "Venue"  ORDER BY id DESC LIMIT 10;
    #   SELECT id, name, city, state FROM "Artist" ORDER BY id DESC LIMIT 10;
    recent_venues = Venue.query.order_by(Venue.id.desc()).limit(10).all()
    recent_artists = Artist.query.order_by(Artist.id.desc()).limit(10).all()
    return render_template('pages/home.html', recent_venues=recent_venues, recent_artists=recent_artists)


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    # SQL equivalent:
    #   SELECT id, name, city, state FROM "Venue" ORDER BY state, city;
    #   SELECT COUNT(*) FROM "Show"
    #     WHERE venue_id = :venue_id AND start_time > NOW();
    all_venues = Venue.query.order_by(Venue.state, Venue.city).all()
    now = datetime.now()

    areas = {}
    for venue in all_venues:
        key = (venue.city, venue.state)
        num_upcoming_shows = Show.query.filter(
            Show.venue_id == venue.id,
            Show.start_time > now
        ).count()

        if key not in areas:
            areas[key] = {'city': venue.city, 'state': venue.state, 'venues': []}
        areas[key]['venues'].append({
            'id': venue.id,
            'name': venue.name,
            'num_upcoming_shows': num_upcoming_shows,
        })

    return render_template('pages/venues.html', areas=list(areas.values()))


@app.route('/venues/search', methods=['POST'])
def search_venues():
    # SQL equivalent:
    #   SELECT id, name FROM "Venue"
    #   WHERE LOWER(name) LIKE LOWER('%' || :search_term || '%');
    search_term = request.form.get('search_term', '')
    now = datetime.now()

    venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()

    data = []
    for venue in venues:
        num_upcoming_shows = Show.query.filter(
            Show.venue_id == venue.id,
            Show.start_time > now
        ).count()
        data.append({'id': venue.id, 'name': venue.name, 'num_upcoming_shows': num_upcoming_shows})

    response = {'count': len(data), 'data': data}
    return render_template('pages/search_venues.html', results=response, search_term=search_term)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query.get_or_404(venue_id)
    now = datetime.now()

    # SQL equivalent for past shows:
    #   SELECT s.id, s.start_time,
    #          a.id AS artist_id, a.name AS artist_name, a.image_link AS artist_image_link
    #   FROM "Show" s
    #   JOIN "Artist" a ON s.artist_id = a.id
    #   WHERE s.venue_id = :venue_id AND s.start_time < NOW();
    past_shows_query = (
        db.session.query(Show).join(Artist)
        .filter(Show.venue_id == venue_id, Show.start_time < now)
        .all()
    )

    # SQL equivalent for upcoming shows:
    #   SELECT s.id, s.start_time,
    #          a.id AS artist_id, a.name AS artist_name, a.image_link AS artist_image_link
    #   FROM "Show" s
    #   JOIN "Artist" a ON s.artist_id = a.id
    #   WHERE s.venue_id = :venue_id AND s.start_time >= NOW();
    upcoming_shows_query = (
        db.session.query(Show).join(Artist)
        .filter(Show.venue_id == venue_id, Show.start_time >= now)
        .all()
    )

    past_shows = [{
        'artist_id': show.artist.id,
        'artist_name': show.artist.name,
        'artist_image_link': show.artist.image_link,
        'start_time': show.start_time,
    } for show in past_shows_query]

    upcoming_shows = [{
        'artist_id': show.artist.id,
        'artist_name': show.artist.name,
        'artist_image_link': show.artist.image_link,
        'start_time': show.start_time,
    } for show in upcoming_shows_query]

    data = {
        'id': venue.id,
        'name': venue.name,
        'genres': [g.name for g in venue.genres],  # convert Genre objects to strings
        'address': venue.address,
        'city': venue.city,
        'state': venue.state,
        'phone': venue.phone,
        'website': venue.website_link,
        'facebook_link': venue.facebook_link,
        'seeking_talent': venue.seeking_talent,
        'seeking_description': venue.seeking_description,
        'image_link': venue.image_link,
        'past_shows': past_shows,
        'upcoming_shows': upcoming_shows,
        'past_shows_count': len(past_shows),
        'upcoming_shows_count': len(upcoming_shows),
    }
    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    # SQL equivalent:
    #   INSERT INTO "Venue" (name, city, state, address, phone, image_link,
    #       facebook_link, website_link, seeking_talent, seeking_description)
    #   VALUES (:name, :city, :state, :address, :phone, :image_link,
    #       :facebook_link, :website_link, :seeking_talent, :seeking_description);
    #
    #   INSERT INTO venue_genres (venue_id, genre_id) VALUES (:venue_id, :genre_id);
    form = VenueForm()
    if form.validate_on_submit():
        try:
            venue = Venue(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                address=form.address.data,
                phone=form.phone.data,
                image_link=form.image_link.data,
                facebook_link=form.facebook_link.data,
                website_link=form.website_link.data,
                seeking_talent=form.seeking_talent.data,
                seeking_description=form.seeking_description.data,
            )
            venue.genres = get_or_create_genres(form.genres.data)
            db.session.add(venue)
            db.session.commit()
            flash('Venue ' + form.name.data + ' was successfully listed!')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Venue ' + form.name.data + ' could not be listed.')
            app.logger.error(f'Error creating venue: {e}')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error in {field}: {error}')
    return render_template('pages/home.html')


@app.route('/venues/<int:venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    # SQL equivalent:
    #   DELETE FROM "Venue" WHERE id = :venue_id;
    #   (cascade deletes associated rows in Show and venue_genres)
    try:
        venue = Venue.query.get_or_404(venue_id)
        db.session.delete(venue)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error deleting venue: {e}')
        abort(500)


#  Artists
#  ----------------------------------------------------------------

@app.route('/artists')
def artists():
    # SQL equivalent:
    #   SELECT id, name FROM "Artist" ORDER BY name;
    data = Artist.query.with_entities(Artist.id, Artist.name).order_by(Artist.name).all()
    artists_list = [{'id': a.id, 'name': a.name} for a in data]
    return render_template('pages/artists.html', artists=artists_list)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    # SQL equivalent:
    #   SELECT id, name FROM "Artist"
    #   WHERE LOWER(name) LIKE LOWER('%' || :search_term || '%');
    search_term = request.form.get('search_term', '')
    now = datetime.now()

    artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()

    data = []
    for artist in artists:
        num_upcoming_shows = Show.query.filter(
            Show.artist_id == artist.id,
            Show.start_time > now
        ).count()
        data.append({'id': artist.id, 'name': artist.name, 'num_upcoming_shows': num_upcoming_shows})

    response = {'count': len(data), 'data': data}
    return render_template('pages/search_artists.html', results=response, search_term=search_term)


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = Artist.query.get_or_404(artist_id)
    now = datetime.now()

    # SQL equivalent for past shows:
    #   SELECT s.id, s.start_time,
    #          v.id AS venue_id, v.name AS venue_name, v.image_link AS venue_image_link
    #   FROM "Show" s
    #   JOIN "Venue" v ON s.venue_id = v.id
    #   WHERE s.artist_id = :artist_id AND s.start_time < NOW();
    past_shows_query = (
        db.session.query(Show).join(Venue)
        .filter(Show.artist_id == artist_id, Show.start_time < now)
        .all()
    )

    # SQL equivalent for upcoming shows:
    #   SELECT s.id, s.start_time,
    #          v.id AS venue_id, v.name AS venue_name, v.image_link AS venue_image_link
    #   FROM "Show" s
    #   JOIN "Venue" v ON s.venue_id = v.id
    #   WHERE s.artist_id = :artist_id AND s.start_time >= NOW();
    upcoming_shows_query = (
        db.session.query(Show).join(Venue)
        .filter(Show.artist_id == artist_id, Show.start_time >= now)
        .all()
    )

    past_shows = [{
        'venue_id': show.venue.id,
        'venue_name': show.venue.name,
        'venue_image_link': show.venue.image_link,
        'start_time': show.start_time,
    } for show in past_shows_query]

    upcoming_shows = [{
        'venue_id': show.venue.id,
        'venue_name': show.venue.name,
        'venue_image_link': show.venue.image_link,
        'start_time': show.start_time,
    } for show in upcoming_shows_query]

    data = {
        'id': artist.id,
        'name': artist.name,
        'genres': [g.name for g in artist.genres],  # convert Genre objects to strings
        'city': artist.city,
        'state': artist.state,
        'phone': artist.phone,
        'website': artist.website_link,
        'facebook_link': artist.facebook_link,
        'seeking_venue': artist.seeking_venue,
        'seeking_description': artist.seeking_description,
        'image_link': artist.image_link,
        'past_shows': past_shows,
        'upcoming_shows': upcoming_shows,
        'past_shows_count': len(past_shows),
        'upcoming_shows_count': len(upcoming_shows),
    }
    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------

@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.get_or_404(artist_id)
    form = ArtistForm(obj=artist)
    # SelectMultipleField expects strings; convert Genre objects to names
    form.genres.data = [g.name for g in artist.genres]
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # SQL equivalent:
    #   UPDATE "Artist"
    #   SET name=:name, city=:city, state=:state, phone=:phone, image_link=:image_link,
    #       facebook_link=:facebook_link, website_link=:website_link,
    #       seeking_venue=:seeking_venue, seeking_description=:seeking_description
    #   WHERE id = :artist_id;
    #
    #   DELETE FROM artist_genres WHERE artist_id = :artist_id;
    #   INSERT INTO artist_genres (artist_id, genre_id) VALUES (:artist_id, :genre_id);
    artist = Artist.query.get_or_404(artist_id)
    form = ArtistForm()
    if form.validate_on_submit():
        try:
            artist.name = form.name.data
            artist.city = form.city.data
            artist.state = form.state.data
            artist.phone = form.phone.data
            artist.image_link = form.image_link.data
            artist.facebook_link = form.facebook_link.data
            artist.website_link = form.website_link.data
            artist.seeking_venue = form.seeking_venue.data
            artist.seeking_description = form.seeking_description.data
            artist.genres = get_or_create_genres(form.genres.data)
            db.session.commit()
            flash(f'Artist {artist.name} was successfully updated!')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred. Artist {artist.name} could not be updated.')
            app.logger.error(f'Error updating artist: {e}')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error in {field}: {error}')
    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.get_or_404(venue_id)
    form = VenueForm(obj=venue)
    # SelectMultipleField expects strings; convert Genre objects to names
    form.genres.data = [g.name for g in venue.genres]
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    # SQL equivalent:
    #   UPDATE "Venue"
    #   SET name=:name, city=:city, state=:state, address=:address, phone=:phone,
    #       image_link=:image_link, facebook_link=:facebook_link, website_link=:website_link,
    #       seeking_talent=:seeking_talent, seeking_description=:seeking_description
    #   WHERE id = :venue_id;
    #
    #   DELETE FROM venue_genres WHERE venue_id = :venue_id;
    #   INSERT INTO venue_genres (venue_id, genre_id) VALUES (:venue_id, :genre_id);
    venue = Venue.query.get_or_404(venue_id)
    form = VenueForm()
    if form.validate_on_submit():
        try:
            venue.name = form.name.data
            venue.city = form.city.data
            venue.state = form.state.data
            venue.address = form.address.data
            venue.phone = form.phone.data
            venue.image_link = form.image_link.data
            venue.facebook_link = form.facebook_link.data
            venue.website_link = form.website_link.data
            venue.seeking_talent = form.seeking_talent.data
            venue.seeking_description = form.seeking_description.data
            venue.genres = get_or_create_genres(form.genres.data)
            db.session.commit()
            flash(f'Venue {venue.name} was successfully updated!')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred. Venue {venue.name} could not be updated.')
            app.logger.error(f'Error updating venue: {e}')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error in {field}: {error}')
    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    # SQL equivalent:
    #   INSERT INTO "Artist" (name, city, state, phone, image_link, facebook_link,
    #       website_link, seeking_venue, seeking_description)
    #   VALUES (:name, :city, :state, :phone, :image_link, :facebook_link,
    #       :website_link, :seeking_venue, :seeking_description);
    #
    #   INSERT INTO artist_genres (artist_id, genre_id) VALUES (:artist_id, :genre_id);
    form = ArtistForm()
    if form.validate_on_submit():
        try:
            artist = Artist(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                phone=form.phone.data,
                image_link=form.image_link.data,
                facebook_link=form.facebook_link.data,
                website_link=form.website_link.data,
                seeking_venue=form.seeking_venue.data,
                seeking_description=form.seeking_description.data,
            )
            artist.genres = get_or_create_genres(form.genres.data)
            db.session.add(artist)
            db.session.commit()
            flash('Artist ' + form.name.data + ' was successfully listed!')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Artist ' + form.name.data + ' could not be listed.')
            app.logger.error(f'Error creating artist: {e}')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error in {field}: {error}')
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # SQL equivalent:
    #   SELECT s.id, s.start_time,
    #          v.id AS venue_id, v.name AS venue_name,
    #          a.id AS artist_id, a.name AS artist_name, a.image_link AS artist_image_link
    #   FROM "Show" s
    #   JOIN "Venue"  v ON s.venue_id  = v.id
    #   JOIN "Artist" a ON s.artist_id = a.id
    #   ORDER BY s.start_time DESC;
    all_shows = (
        db.session.query(Show).join(Venue).join(Artist)
        .order_by(Show.start_time.desc())
        .all()
    )
    data = [{
        'venue_id': show.venue_id,
        'venue_name': show.venue.name,
        'artist_id': show.artist_id,
        'artist_name': show.artist.name,
        'artist_image_link': show.artist.image_link,
        'start_time': show.start_time,
    } for show in all_shows]
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    # SQL equivalent:
    #   INSERT INTO "Show" (artist_id, venue_id, start_time)
    #   VALUES (:artist_id, :venue_id, :start_time);
    form = ShowForm()
    if form.validate_on_submit():
        try:
            artist_id = form.artist_id.data
            venue_id = form.venue_id.data

            artist = Artist.query.get(artist_id)
            venue = Venue.query.get(venue_id)

            if not artist:
                flash(f'Artist with ID {artist_id} does not exist.')
                return render_template('forms/new_show.html', form=form)
            if not venue:
                flash(f'Venue with ID {venue_id} does not exist.')
                return render_template('forms/new_show.html', form=form)

            show = Show(
                artist_id=artist_id,
                venue_id=venue_id,
                start_time=form.start_time.data,
            )
            db.session.add(show)
            db.session.commit()
            flash('Show was successfully listed!')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Show could not be listed.')
            app.logger.error(f'Error creating show: {e}')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error in {field}: {error}')
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

if __name__ == '__main__':
    app.run()
