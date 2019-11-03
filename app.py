#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import sys
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
from models import *
from datetime import datetime
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# TODO: connect to a local postgresql database

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format = "EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format = "EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  """Displays all venues grouped by their city and state.

  Returns:
      template -- An HTML template/page with all venues returned from the database query for all venues.
  """
  try:
    # create a new data list
    data = []
    # select all distinct cities and states from the venues table
    distinct_state_and_cities = Venue.query.distinct(Venue.city, Venue.state).all()

    for index, distinct_venue in enumerate(distinct_state_and_cities):
      # loop through the results of the distinct values and create a dictionary for every city/state
      venue_details = { 'venues': [] }
      venue_details['city'] = distinct_state_and_cities[index].city
      venue_details['state'] = distinct_state_and_cities[index].state
      # get all venues for a city/state in a list
      venues = Venue.query.filter(Venue.city == distinct_state_and_cities[index].city, Venue.state == distinct_state_and_cities[index].state).all()
      for venue in venues:
        # loop through the list of venues and create a venue object that contains the number of upcoming shows for each venue
        current_time = datetime.now()
        venue_dict = {}
        venue_dict['id'] = venue.id
        venue_dict['name'] = venue.name
        venue_dict['upcoming_shows'] = Venue.query.filter(Venue.id == venue.id, Show.venue_id == venue.id, Show.start_time > current_time).count()

        venue_details['venues'].append(venue_dict)
      data.append(venue_details)
  except:
    db.session.rollback()
  finally:
    db.session.close()

  # TODO: replace with real venues data.
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
  """shows a venue search result page with the given search term.

  Returns:
      template -- An HTML template that displays the venues that match the search term entered.
  """
  try:
    search_term = request.form['search_term']
    keywords = '%{}%'.format(search_term)
    data = []
    response = {}
    # query the venue table to get venues whose names match the search term regardless of the character casing
    count = Venue.query.filter(Venue.name.ilike(keywords)).count()
    venues = Venue.query.filter(Venue.name.ilike(keywords)).all()
    current_time = datetime.now()

    for index, venue in enumerate(venues):
      # loop through the list of venues and create a venue object for each venue,
      # that contains the number of upcoming shows for each venue
      venue_dict = {}
      upcoming_shows_count = Venue.query.filter(Venue.id == venue.id, Show.venue_id == venue.id, Show.start_time > current_time).count()
      venue_dict['id'] = venues[index].id
      venue_dict['name'] = venues[index].name
      venue_dict['upcoming_shows_count'] = upcoming_shows_count
      data.append(venue_dict)
    response['count'] = count
    response['data'] = data
  except:
    db.session.rollback()
  finally:
    db.session.close()
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  """shows the venue page with the given venue_id.

  Arguments:
      venue_id {integer} -- The ID of the venue to be displayed.

  Returns:
      template -- An HTML template/page that displays a venue matching the ID provided in the request.
  """
  try:
    data = {'upcoming_shows': [], 'past_shows': [],
        'upcoming_shows_count': 0, 'past_shows_count': 0}
    current_time = datetime.now()

    # find the venue with the matching ID from the table
    venue = Venue.query.get(venue_id)
    for index, show in enumerate(venue.shows):
      # get the all the shows for a venue and group them by upcoming and past events
      if show.start_time > current_time:
        show_data = {}
        data['upcoming_shows_count'] = data['upcoming_shows_count'] + 1
        show_data['artist_id'] = venue.shows[index].artist.id
        show_data['artist_name'] = venue.shows[index].artist.name
        show_data['artist_image_link'] = venue.shows[index].artist.image_link
        show_data['start_time'] = format_datetime(str(show.start_time))
        data['upcoming_shows'].append(show_data)
      elif show.start_time < current_time:
        show_data = {}
        data['past_shows_count'] = data['past_shows_count'] + 1
        show_data['artist_id'] = venue.shows[index].artist.id
        show_data['artist_name'] = venue.shows[index].artist.name
        show_data['artist_image_link'] = venue.shows[index].artist.image_link
        show_data['start_time'] = format_datetime(str(show.start_time))
        data['past_shows'].append(show_data)
    data['id'] = venue.id
    data['name'] = venue.name
    data['genres'] = venue.genres
    data['address'] = venue.address
    data['city'] = venue.city
    data['state'] = venue.state
    data['phone'] = venue.phone
    data['website'] = venue.website
    data['facebook_link'] = venue.facebook_link
    data['seeking_talent'] = venue.seeking_talent
    data['seeking_description'] = venue.seeking_description
    data['image_link'] = venue.image_link
  except:
    db.session.rollback()
  finally:
    return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  """creates a new venue with data submitted from the frontend form.

  Returns:
      template -- An HTML template/page of the homepage with a flash message about the success or failure of the request.
  """
  error = False
  body = {}
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    address = request.form['address']
    phone = request.form['phone']
    website = request.form['website']
    image_link = request.form['image_link']
    facebook_link = request.form['facebook_link']
    genres = request.form['genres'].split(', ')

    venue = Venue(name=name, city=city, state=state, address=address, phone=phone, website=website, image_link=image_link, facebook_link=facebook_link, genres=genres)
    db.session.add(venue)
    db.session.commit()

    body = venue.as_dict()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()
    if error:
      flash('An error occured while creating the venue')
    else:
      flash('Venue ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  """Deletes a venue with the provided venue ID.

  Arguments:
      venue_id {integer} -- The ID of the venue to be deleted

  Returns:
      template -- An HTML template/page of the homepage with a flash message about the success or failure of the request
  """
  error = False
  try:
    Venue.query.filter_by(id=venue_id).delete()
    db.session.commit()
  except:
    db.session.rollback()
    error = True
  finally:
    db.session.close()
    if error:
      flash('An error occured while trying to delete the venue')
      return render_template('pages/venues.html')
    else:
      flash('Venue successfully deleted')
      return render_template('pages/home.html')

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  """Displays all artists with their names.

  Returns:
      template -- An HTML template/page with all artists returned from the database query for all artists.
  """
  try:
    data = []

    artists = Artist.query.order_by('id').all()

    for index, artist in enumerate(artists):
      artist_data = {}
      artist_data['id'] = artists[index].id
      artist_data['name'] = artists[index].name
      data.append(artist_data)
  except:
    db.session.rollback()
  finally:
    return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  """shows an artists search result page with the given search term.

  Returns:
      template -- An HTML template that displays the venues that match the search term entered.
  """
  try:
    search_term = request.form['search_term']
    keywords = '%{}%'.format(search_term)
    data = []
    response = {}
    count = Artist.query.filter(Artist.name.ilike(keywords)).count()
    artists = Artist.query.filter(Artist.name.ilike(keywords)).all()
    current_time = datetime.now()

    for index, artist in enumerate(artists):
      artist_dict = {}
      upcoming_shows_count = Artist.query.filter(Artist.id == artist.id, Show.artist_id == artist.id, Show.start_time > current_time).count()
      artist_dict['id'] = artists[index].id
      artist_dict['name'] = artists[index].name
      artist_dict['upcoming_shows_count'] = upcoming_shows_count
      data.append(artist_dict)
    response['count'] = count
    response['data'] = data
  except:
    db.session.rollback()
  finally:
    db.session.close()
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  """shows an artist's page with the given artist ID.

  Arguments:
      artist_id {integer} -- The ID of the artist to be displayed.

  Returns:
      template -- An HTML template/page that displays an artist matching the ID provided in the request.
  """
  try:
    data = {'upcoming_shows': [], 'past_shows': [],
        'upcoming_shows_count': 0, 'past_shows_count': 0}
    current_time = datetime.now()
    artist = Artist.query.get(artist_id)

    if len(artist.shows) > 0:
      for index, show in enumerate(artist.shows):
        if show.start_time > current_time:
          show_data = {}
          data['upcoming_shows_count'] = data['upcoming_shows_count'] + 1
          show_data['venue_id'] = artist.shows[index].venue.id
          show_data['venue_name'] = artist.shows[index].venue.name
          show_data['venue_image_link'] = artist.shows[index].venue.image_link
          show_data['start_time'] = format_datetime(str(show.start_time))
          data['upcoming_shows'].append(show_data)
        elif show.start_time < current_time:
          show_data = {}
          data['past_shows_count'] = data['past_shows_count'] + 1
          show_data['venue_id'] = artist.shows[index].venue.id
          show_data['venue_name'] = artist.shows[index].venue.name
          show_data['venue_image_link'] = artist.shows[index].venue.image_link
          show_data['start_time'] = format_datetime(str(show.start_time))
          data['past_shows'].append(show_data)
      data['id'] = artist.id
      data['name'] = artist.name
      data['genres'] = artist.genres
      data['city'] = artist.city
      data['state'] = artist.state
      data['phone'] = artist.phone
      data['facebook_link'] = artist.facebook_link
      data['seeking_venue'] = artist.seeking_venue
      data['seeking_description'] = artist.seeking_description
      data['image_link'] = artist.image_link
  except:
    db.sesssion.rollback()
  finally:
    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  """displays a page where an artists information can be updated.

  Arguments:
      artist_id {integer} -- The ID of the artist whose information is to be updated.

  Returns:
      template -- An HTML page with a form for the fields to be updated
  """
  form = ArtistForm()
  artist = Artist.query.get(artist_id)
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  """Updates an artist's information.

  Arguments:
      artist_id {integer} -- The ID of the artist whose information will be updated.

  Returns:
      template -- An HTML page that shows the artist's page with the new information
  """
  error = False
  try:
    artist = Artist.query.get(artist_id)
    artist.name = request.form['name'] if len(request.form['name']) > 0 else artist.name
    artist.city = request.form['city'] if len(request.form['city']) > 0 else artist.city
    artist.state = request.form['state'] if len(request.form['state']) > 0 else artist.state
    artist.phone = request.form['phone'] if len(request.form['phone']) > 0 else artist.phone
    artist.facebook_link = request.form['facebook_link'] if len(request.form['facebook_link']) > 0 else artist.facebook_link
    artist.image_link = request.form['image_link'] if len(request.form['image_link']) > 0 else artist.image_link
    artist.genres = request.form['genres'].split(', ') if len(request.form['genres']) > 0 else artist.genres
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()
    if error:
      flash('An error occured while updating the artist')
    else:
      flash('Artist ' + request.form['name'] + ' was successfully updated!')
    return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  """displays a page where a venue's information can be updated.

  Arguments:
      venue_id {intger} -- The ID of the venue whose information is to be updated

  Returns:
      template -- An HTML page with a form for the fields to be updated
  """
  form = VenueForm()
  venue = Venue.query.get(venue_id)
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  """Updates a venue's information

  Arguments:
      venue_id {integer} -- The ID of the venue whose informatio will be updated

  Returns:
      template -- An HTML page that shows the venue's page with the new information
  """
  error = False
  try:
    venue = Venue.query.get(venue_id)
    venue.name = request.form['name'] if len(request.form['name']) > 0 else venue.name
    venue.address = request.form['address'] if len(request.form['address']) > 0 else venue.address
    venue.city = request.form['city'] if len(request.form['city']) > 0 else venue.city
    venue.state = request.form['state'] if len(request.form['state']) > 0 else venue.state
    venue.phone = request.form['phone'] if len(request.form['phone']) > 0 else venue.phone
    venue.facebook_link = request.form['facebook_link'] if len(request.form['facebook_link']) > 0 else venue.facebook_link
    venue.image_link = request.form['image_link'] if len(request.form['image_link']) > 0 else venue.image_link
    venue.genres = request.form['genres'].split(', ') if len(request.form['genres']) > 0 else venue.genres
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()
    if error:
      flash('An error occured while updating the venue')
    else:
      flash('Venue ' + request.form['name'] + ' was successfully updated!')
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  """dispays a page with a form where a new artist can be added

  Returns:
      template -- An HTML page showing form with the fields required when adding a new artist
  """
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  """Creates a new artist with the data submitted from the frontend form.

  Returns:
      template -- An HTML template/page of the homepage with a flash message about the success or failure of the request
  """
  error = False
  body = {}
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    phone = request.form['phone']
    image_link = request.form['image_link']
    facebook_link = request.form['facebook_link']
    genres = request.form['genres'].split(', ')

    artist = Artist(name=name, city=city, state=state, phone=phone, facebook_link=facebook_link, image_link=image_link, genres=genres)
    db.session.add(artist)
    db.session.commit()
    body = artist.as_dict()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()
    if error:
      flash('An error occured while creating the artist')
      return render_template('pages/home.html')
    else:
      flash('Artist ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  """Displays a list of all shows with the venues and artists.

  Returns:
      template -- An HTML page that displays the shows listed
  """
  try:
    data = []
    shows = Show.query.all()

    for show in shows:
      venue = Venue.query.get(show.venue_id)
      artist = Artist.query.get(show.artist_id)
      show_data = {}
      show_data['venue_id'] = show.venue_id
      show_data['venue_name'] = venue.name
      show_data['artist_id'] = artist.id
      show_data['artist_name'] = artist.name
      show_data['artist_image_link'] = artist.image_link
      show_data['start_time'] = format_datetime(str(show.start_time))
      data.append(show_data)
  except:
    db.session.rollback()
  finally:
    db.session.close()
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  """Creates a show with the data submitted on the frontend form.

  Returns:
      template -- An HTML template/page of the homepage with a flash message about the success or failure of the request.
  """
  error = False
  try:
    artist_id = request.form['artist_id']
    venue_id = request.form['venue_id']
    start_time = request.form['start_time']

    show = Show(artist_id=artist_id, venue_id=venue_id, start_time=start_time)
    db.session.add(show)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()
    if error:
      flash('An error occured and the show could not be added')
    else:
      flash('Show was successfully listed!')
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

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
