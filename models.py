from app import db

# ---------------------------------------------------------------------------
# Many-to-many association tables: Artist/Venue ↔ Genre
# Composite primary keys provide implicit uniqueness (no duplicate rows).
# ---------------------------------------------------------------------------

venue_genres = db.Table(
    'venue_genres',
    db.Column('venue_id', db.Integer, db.ForeignKey('Venue.id'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('Genre.id'), primary_key=True)
)

artist_genres = db.Table(
    'artist_genres',
    db.Column('artist_id', db.Integer, db.ForeignKey('Artist.id'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('Genre.id'), primary_key=True)
)


class Genre(db.Model):
    """Lookup table for music genres — normalized out of Artist and Venue (1NF/3NF)."""
    __tablename__ = 'Genre'

    id = db.Column(db.Integer, primary_key=True)
    # unique=True: database-level constraint; no two rows may share a genre name
    name = db.Column(db.String(120), nullable=False, unique=True)

    def __repr__(self):
        return f'<Genre {self.name}>'


class Venue(db.Model):
    __tablename__ = 'Venue'
    __table_args__ = (
        # Database-level constraint: same venue name at the same address is a duplicate
        db.UniqueConstraint('name', 'address', name='uq_venue_name_address'),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(500))
    seeking_talent = db.Column(db.Boolean, default=False, nullable=False)
    seeking_description = db.Column(db.String(500))
    # genres is a 3NF-normalized relationship via the venue_genres association table
    genres = db.relationship('Genre', secondary=venue_genres, lazy='subquery')
    shows = db.relationship('Show', backref='venue', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Venue {self.id} {self.name}>'


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(500))
    seeking_venue = db.Column(db.Boolean, default=False, nullable=False)
    seeking_description = db.Column(db.String(500))
    # genres is a 3NF-normalized relationship via the artist_genres association table
    genres = db.relationship('Genre', secondary=artist_genres, lazy='subquery')
    shows = db.relationship('Show', backref='artist', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Artist {self.id} {self.name}>'


class Show(db.Model):
    __tablename__ = 'Show'
    __table_args__ = (
        # Database-level constraint: an artist cannot be double-booked at the same venue and time
        db.UniqueConstraint('artist_id', 'venue_id', 'start_time', name='uq_show_booking'),
    )

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Show {self.id} venue={self.venue_id} artist={self.artist_id}>'
