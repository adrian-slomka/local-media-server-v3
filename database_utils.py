from __future__ import annotations
from sqlalchemy import create_engine, MetaData, DateTime, Table, Column, Integer, String, Float, Boolean, ForeignKey, UniqueConstraint, desc, asc, or_
from sqlalchemy.orm import scoped_session, Mapped, mapped_column, sessionmaker, declarative_base, relationship, joinedload
from sqlalchemy.inspection import inspect
from datetime import datetime, timezone
from random import randint
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
load_dotenv()

import os
import secrets
import json
import logging
logger = logging.getLogger(__name__)

# GLOBAL VARIABLE
last_updated_flag = False


db = create_engine(
    'sqlite:///localdb.db',
    connect_args={"check_same_thread": False},
    future=True
)
session_factory = sessionmaker(bind=db)
Session = scoped_session(session_factory)
Base = declarative_base()

def create_localdb():
    if os.path.exists('localdb.db'):
        return    
    
    Base.metadata.create_all(db)
    
    with Session() as session:
        # Preload the characters table with a default entry "NO CHARACTER".
        # This serves as a fallback for actors who don't have a specified character name,
        # such as background extras or special cases.
        # When an actor lacks a character name, they can be linked to this default entry.
        insert_characters(session, ['NO CHARACTER'])
        session.commit() 


    # Add default admin account
    admin_password = os.getenv('DEFAULT_ADMIN_ACCOUNT')
    if not admin_password:
        logger.warning("Missing DEFAULT_ADMIN_ACCOUNT in environment. Admin account not created.")
        return     
    password = generate_password_hash(admin_password)
    key = secrets.token_hex(8)
    insert_new_user(password, key, is_admin=True, is_adult=True)


def add_account(password_string: str, is_admin=False, is_adult=True):
    if not password_string or not isinstance(password_string, str):
        print('user account creation failed: password must be a non-empty password_string')
        logger.error('user account creation failed: password must be a non-empty password_string')
        return

    if ' ' in password_string:
        print("user account creation failed: password cannot contain spaces")
        logger.error("user account creation failed: password cannot contain spaces")
        return

    min_length = 4
    max_length = 100
    if not (min_length <= len(password_string) <= max_length):
        print('user account creation failed: password cannot contain spaces')
        logger.error(f"user account creation failed: password must be at least {min_length} and be less than {max_length} characters long")
        return

    normalized = password_string.strip()
    if not normalized:
        print('user account creation failed: password cannot be only spaces')
        logger.error("user account creation failed: password cannot be only spaces")
        return

    try:
        password = generate_password_hash(normalized)
    except Exception as e:
        print(f"user account creation failed: exception during password hashing {e}")
        logger.error(f"user account creation failed: exception during password hashing {e}", exc_info=True)
        raise
    
    try:
        key = secrets.token_hex(8)
    except Exception as e:
        print(f"user account creation failed: exception during generating {e}")
        logger.error(f"user account creation failed: exception during generating {e}", exc_info=True)
        raise
    
    insert_new_user(password, key, is_admin, is_adult)




media_genres = Table(
    'media_genres',
    Base.metadata,
    Column('media_id', ForeignKey('media_items.id', ondelete="CASCADE"), primary_key=True, index=True),
    Column('genre_id', ForeignKey('genres.id', ondelete="CASCADE"), primary_key=True, index=True)
)

media_content_ratings = Table(
    'media_content_ratings',
    Base.metadata,
    Column('media_id', ForeignKey('media_items.id', ondelete="CASCADE"), primary_key=True, index=True),
    Column('content_rating_id', ForeignKey('content_ratings.id', ondelete="CASCADE"), primary_key=True, index=True)
)

media_production_companies = Table(
    'media_production_companies',
    Base.metadata,
    Column('media_id', ForeignKey('media_items.id', ondelete="CASCADE"), primary_key=True, index=True),
    Column('production_company_id', ForeignKey('production_companies.id', ondelete="CASCADE"), primary_key=True, index=True)
)

media_networks = Table(
    'media_networks',
    Base.metadata,
    Column('media_id', ForeignKey('media_items.id', ondelete="CASCADE"), primary_key=True),
    Column('network_id', ForeignKey('networks.id', ondelete="CASCADE"), primary_key=True)
)




class MediaType():
    MOVIE = 'movie'
    TV = 'tv'


class MediaItem(Base):
    __tablename__ = 'media_items'

    id: Mapped[int] = mapped_column(primary_key=True, index=True, unique=True)
    media_type: Mapped[str] = mapped_column(nullable=True)
    tmdb_id: Mapped[int] = mapped_column(nullable=True)
    imdb_id: Mapped[int] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(nullable=True, index=True)
    original_title: Mapped[str] = mapped_column(nullable=True)
    release_date: Mapped[str] = mapped_column(nullable=True)
    tagline: Mapped[str] = mapped_column(nullable=True)
    overview: Mapped[str] = mapped_column(nullable=True)
    backdrop_path: Mapped[str] = mapped_column(nullable=True)
    poster_path: Mapped[str] = mapped_column(nullable=True)
    homepage: Mapped[str] = mapped_column(nullable=True)
    popularity: Mapped[float] = mapped_column(nullable=True)
    vote_average: Mapped[float] = mapped_column(nullable=True)
    vote_count: Mapped[int] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=True)
    hash_key: Mapped[str] = mapped_column(nullable=False, unique=True)
    entry_created: Mapped[int] = mapped_column(nullable=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)
    new_video_inserted: Mapped[int] = mapped_column(nullable=True)

    # Many to Many
    genres: Mapped[list[Genre]] = relationship(secondary=media_genres, back_populates='media_item')
    content_ratings: Mapped[list[ContentRating]] = relationship(secondary=media_content_ratings, back_populates='media_item')
    production_companies: Mapped[list[ProductionCompany]] = relationship(secondary=media_production_companies, back_populates='media_item')
    networks: Mapped[list[Network]] = relationship(secondary=media_networks, back_populates='media_item')
    media_cast: Mapped[list[MediaCast]] = relationship(back_populates='media_item', cascade='all, delete-orphan')
    # One to Many
    videos: Mapped[list[Video]] = relationship(back_populates='media_item', cascade='all, delete-orphan')
    logos: Mapped[list[Logo]] = relationship(back_populates='media_item', foreign_keys='Logo.media_id', cascade='all, delete-orphan')
    media_metadata: Mapped[list[VideoMetadata]] = relationship(back_populates='media_item', cascade='all, delete-orphan')
    # One to One
    movie_details: Mapped[MovieDetails] = relationship(back_populates='media_item', cascade='all, delete-orphan')
    tv_details: Mapped[TvDetails] = relationship(back_populates='media_item', cascade='all, delete-orphan')


    # # includes relationships
    # def __repr__(self):
    #     mapper = inspect(self.__class__)
    #     attrs = {c.key: getattr(self, c.key) for c in mapper.attrs}
    #     attr_str = '\n'.join(f"{k}={v!r}" for k, v in attrs.items())
    #     return f"<{self.__class__.__name__}({attr_str})>"

    # only columns
    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = '\n'.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"


class MovieDetails(Base):
    __tablename__ = 'media_details_movie'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    media_id: Mapped[int] = mapped_column(ForeignKey('media_items.id', ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    budget: Mapped[int] = mapped_column(nullable=True)
    revenue: Mapped[int] = mapped_column(nullable=True)
    runtime: Mapped[int] = mapped_column(nullable=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)

    media_item: Mapped[MediaItem] = relationship(back_populates='movie_details')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = '\n'.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"


class TvDetails(Base):
    __tablename__ = 'media_details_tv'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    media_id: Mapped[int] = mapped_column(ForeignKey('media_items.id', ondelete="CASCADE"), unique=True, nullable=False, index=True)

    first_air_date: Mapped[str] = mapped_column(nullable=True)
    last_air_date: Mapped[str] = mapped_column(nullable=True)
    number_of_seasons: Mapped[int] = mapped_column(nullable=True)
    number_of_episodes: Mapped[int] = mapped_column(nullable=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)

    media_item: Mapped[MediaItem] = relationship(back_populates='tv_details')
    seasons: Mapped[list[TvSeason]] = relationship(back_populates='tv_details', cascade='all, delete-orphan')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = '\n'.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"


class TvSeason(Base):
    __tablename__ = 'media_details_tv_seasons'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    media_id: Mapped[int] = mapped_column(ForeignKey('media_items.id', ondelete="CASCADE"), nullable=False, index=True)
    tv_id: Mapped[int] = mapped_column(ForeignKey('media_details_tv.id', ondelete="CASCADE"), nullable=False, index=True)
    
    tmdb_season_id: Mapped[int] = mapped_column(nullable=True)
    season_number: Mapped[int] = mapped_column(nullable=True)
    air_date: Mapped[str] = mapped_column(nullable=True)
    episode_count: Mapped[int] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(nullable=True)
    overview: Mapped[str] = mapped_column(nullable=True)
    poster_path: Mapped[str] = mapped_column(nullable=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)

    tv_details: Mapped[TvDetails] = relationship(back_populates='seasons')
    episodes: Mapped[list[TvEpisode]] = relationship(back_populates='tv_season', cascade='all, delete-orphan')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = '\n'.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"


class TvEpisode(Base):
    __tablename__ = 'media_details_tv_seasons_episodes'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    media_id: Mapped[int] = mapped_column(ForeignKey('media_items.id', ondelete="CASCADE"), nullable=False, index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey('media_details_tv_seasons.id', ondelete="CASCADE"), nullable=False, index=True)

    tmdb_episode_id: Mapped[int] = mapped_column(nullable=True)
    air_date: Mapped[str] = mapped_column(nullable=True)
    season_number: Mapped[int] = mapped_column(nullable=True)
    episode_number: Mapped[int] = mapped_column(nullable=True)
    episode_type: Mapped[str] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(nullable=True)
    overview: Mapped[str] = mapped_column(nullable=True)
    runtime: Mapped[int] = mapped_column(nullable=True)
    still_path: Mapped[str] = mapped_column(nullable=True)
    vote_average: Mapped[float] = mapped_column(nullable=True)
    vote_count: Mapped[int] = mapped_column(nullable=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)

    tv_season: Mapped[TvSeason] = relationship(back_populates='episodes')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = '\n'.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"


class Genre(Base):
    __tablename__ = 'genres'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)

    media_item: Mapped[list[MediaItem]] = relationship(secondary=media_genres, back_populates='genres')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"


class ContentRating(Base):
    __tablename__ = 'content_ratings'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    rating: Mapped[str] = mapped_column(nullable=False)
    country: Mapped[str] = mapped_column(nullable=False)

    media_item: Mapped[list[MediaItem]] = relationship(secondary=media_content_ratings, back_populates='content_ratings')

    __table_args__ = (
        UniqueConstraint('rating', 'country', name='uix_rating_country'),
    )

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"


class ProductionCompany(Base):
    __tablename__ = 'production_companies'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    logo_path: Mapped[str] = mapped_column(nullable=True)
    origin_country: Mapped[str] = mapped_column(nullable=True)

    media_item: Mapped[list[MediaItem]] = relationship(secondary=media_production_companies,back_populates='production_companies')
    
    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"


class Network(Base):
    __tablename__ = 'networks'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    logo_path: Mapped[str] = mapped_column(nullable=True)
    origin_country: Mapped[str] = mapped_column(nullable=True)

    media_item: Mapped[list["MediaItem"]] = relationship(secondary=media_networks,back_populates='networks')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"


class Video(Base):
    __tablename__ = 'media_videos'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    media_id: Mapped[int] = mapped_column(ForeignKey('media_items.id', ondelete="CASCADE"), nullable=False, index=True)

    lang: Mapped[str] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(nullable=True)
    key: Mapped[str] = mapped_column(nullable=False, unique=True)
    site: Mapped[str] = mapped_column(nullable=True)
    type: Mapped[str] = mapped_column(nullable=True)
    official: Mapped[int] = mapped_column(nullable=True)
    published_at: Mapped[str] = mapped_column(nullable=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)

    media_item: Mapped[MediaItem] = relationship(back_populates='videos')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"


class Logo(Base):
    __tablename__ = 'media_logos'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    media_id: Mapped[int] = mapped_column(ForeignKey('media_items.id', ondelete="CASCADE"), nullable=False, index=True)
    aspect_ratio: Mapped[float] = mapped_column(nullable=True)
    height: Mapped[int] = mapped_column(nullable=True)
    width: Mapped[int] = mapped_column(nullable=True)
    lang: Mapped[str] = mapped_column(nullable=True)
    file_path: Mapped[str] = mapped_column(nullable=False, unique=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)

    media_item: Mapped[MediaItem] = relationship(back_populates='logos')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"


class VideoMetadata(Base):
    __tablename__ = 'media_metadata'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    media_id: Mapped[int] = mapped_column(ForeignKey('media_items.id', ondelete="CASCADE"), nullable=False, index=True)
    season_number: Mapped[int] = mapped_column(nullable=True)
    episode_number: Mapped[int] = mapped_column(nullable=True)

    file_path: Mapped[str] = mapped_column(nullable=False, unique=True)
    hash_key: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    keyframe_path: Mapped[str] = mapped_column(nullable=True)

    resolution: Mapped[str] = mapped_column(nullable=True)
    extension: Mapped[str] = mapped_column(nullable=True)
    audio_codec: Mapped[str] = mapped_column(nullable=True)
    video_codec: Mapped[str] = mapped_column(nullable=True)
    size: Mapped[str] = mapped_column(nullable=True)
    bitrate: Mapped[str] = mapped_column(nullable=True)
    duration: Mapped[int] = mapped_column(nullable=True)
    frame_rate: Mapped[float] = mapped_column(nullable=True)
    width: Mapped[int] = mapped_column(nullable=True)
    height: Mapped[int] = mapped_column(nullable=True)
    aspect_ratio: Mapped[float] = mapped_column(nullable=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)


    media_item: Mapped[MediaItem] = relationship(back_populates='media_metadata')
    # One to Many
    subtitles: Mapped[list[Subtitle]] = relationship(back_populates='media_metadata', cascade="all, delete-orphan")


    __table_args__ = (UniqueConstraint('media_id', 'season_number', 'episode_number', 'file_path', name='uix_metadata_entry'),)

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"


class Subtitle(Base):
    __tablename__ = 'media_subtitles'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    media_id: Mapped[int] = mapped_column(ForeignKey('media_items.id', ondelete="CASCADE"), nullable=False, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey('media_metadata.id', ondelete='CASCADE'), nullable=False, index=True)
    lang: Mapped[str] = mapped_column(nullable=True)
    label: Mapped[str] = mapped_column(nullable=True)

    file_path: Mapped[str] = mapped_column(nullable=False, unique=True)
    hash_key: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)

    entry_updated: Mapped[int] = mapped_column(nullable=True)

    media_metadata: Mapped[VideoMetadata] = relationship(back_populates='subtitles')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"


class MediaCast(Base):
    __tablename__ = 'media_cast'

    media_id: Mapped[int] = mapped_column(ForeignKey('media_items.id', ondelete="CASCADE"), primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('actors.id', ondelete="CASCADE"), primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True)
    episode_count: Mapped[int] = mapped_column(nullable=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)


    media_item: Mapped[MediaItem] = relationship(back_populates='media_cast')
    actor: Mapped[Actor] = relationship(back_populates='media_cast')
    character: Mapped[Character] = relationship(back_populates='media_cast')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"    


class Character(Base):
    __tablename__ = 'characters'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    character: Mapped[str] = mapped_column(nullable=True, unique=True, index=True)

    media_cast: Mapped[list[MediaCast]] = relationship(back_populates='character')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"        


class Actor(Base):
    __tablename__ = 'actors'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tmdb_id: Mapped[int] = mapped_column(nullable=False, unique=True)
    gender: Mapped[int] = mapped_column(nullable=True)
    known_for_department: Mapped[str] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(nullable=True, index=True)
    original_name: Mapped[str] = mapped_column(nullable=True)
    popularity: Mapped[float] = mapped_column(nullable=True)
    profile_path: Mapped[str] = mapped_column(nullable=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)

    media_cast: Mapped[list[MediaCast]] = relationship(back_populates='actor')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"    


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    password: Mapped[str] = mapped_column(nullable=False)
    key: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    is_adult: Mapped[bool] = mapped_column(nullable=True, default=True)
    is_admin: Mapped[bool] = mapped_column(nullable=True, default=False)

    entry_created: Mapped[int] = mapped_column(nullable=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)

    user_profile: Mapped[UserProfile] = relationship(back_populates='user', uselist=False)
    user_library: Mapped[list[UserLibrary]] = relationship(back_populates='user', cascade="all, delete-orphan")
    user_playback: Mapped[list[UserPlayback]] = relationship(back_populates='user', cascade="all, delete-orphan")

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"    


class UserProfile(Base):
    __tablename__ = 'user_profile'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_key: Mapped[str] = mapped_column(ForeignKey('users.key', ondelete="CASCADE"), nullable=False, index=True)

    profile_name: Mapped[str] = mapped_column(nullable=True)
    profile_picture: Mapped[str] = mapped_column(nullable=True)

    entry_created: Mapped[int] = mapped_column(nullable=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)

    user: Mapped[User] = relationship(back_populates='user_profile')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"   


class UserLibrary(Base):
    __tablename__ = 'user_library'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_key: Mapped[str] = mapped_column(ForeignKey('users.key', ondelete="CASCADE"), nullable=False, index=True)

    media_id: Mapped[int] = mapped_column(ForeignKey('media_items.id', ondelete="CASCADE"), nullable=False, index=True)

    rated: Mapped[int] = mapped_column(nullable=True)
    watchlisted: Mapped[int] = mapped_column(nullable=True)

    entry_created: Mapped[int] = mapped_column(nullable=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)

    user: Mapped[User] = relationship(back_populates='user_library')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"  


class UserPlayback(Base):
    __tablename__ = 'user_playback'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_key: Mapped[str] = mapped_column(ForeignKey('users.key', ondelete="CASCADE"), nullable=False, index=True)

    media_id: Mapped[int] = mapped_column(ForeignKey('media_items.id', ondelete="CASCADE"), nullable=False, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey('media_metadata.id', ondelete="CASCADE"), nullable=False, index=True)

    watched: Mapped[bool] = mapped_column(Boolean, nullable=True)
    paused_at: Mapped[int] = mapped_column(nullable=True)
    video_duration: Mapped[int] = mapped_column(nullable=True)
    watchtime: Mapped[int] = mapped_column(nullable=True)

    entry_created: Mapped[int] = mapped_column(nullable=True)
    entry_updated: Mapped[int] = mapped_column(nullable=True)

    user: Mapped[User] = relationship(back_populates='user_playback')

    def __repr__(self):
        mapper = inspect(self.__class__)
        attrs = {c.key: getattr(self, c.key) for c in mapper.columns}
        attr_str = ', '.join(f"{k}={v!r}" for k, v in attrs.items())
        return f"<{self.__class__.__name__}({attr_str})>"  









def update_attrs_if_changed(obj, data: dict, mapping: dict):
    global last_updated_flag
    updated = False

    for attr, key in mapping.items():
        new_value = data.get(key)
        if getattr(obj, attr) != new_value:
            setattr(obj, attr, new_value)
            updated = True
            last_updated_flag = True

    return updated


def upsert_item(item: MediaItem, data: dict):
    if not item or not data:
        return

    mapping = {
        'media_type': 'media_type',
        'tmdb_id': 'tmdb_id',
        'imdb_id': 'imdb_id',
        'original_title': 'original_title',
        'release_date': 'release_date',
        'tagline': 'tagline',
        'overview': 'overview',
        'backdrop_path': 'backdrop_path',
        'poster_path': 'poster_path',
        'homepage': 'homepage',
        'popularity': 'popularity',
        'vote_average': 'vote_average',
        'vote_count': 'vote_count',
        'status': 'status'
    }

    if update_attrs_if_changed(item, data, mapping):
        item.entry_updated = int(datetime.now(timezone.utc).timestamp())


def insert_genres(session, genres: list):
    existing_genres = {g.name: g for g in session.query(Genre).all()}

    for genre_name in genres:
        if not genre_name and not isinstance(genre_name, str): # skip of genre_name not a string
            logger.warning('error while appending new genre to the session: genre is none or is not a string.')
            continue

        genre = existing_genres.get(genre_name)
        if not genre:
            genre = Genre(name=genre_name)
            session.add(genre)
            existing_genres[genre_name] = genre

    return existing_genres


def insert_content_ratings(session, content_ratings: list[dict]):
    existing_ratings = {(cr.rating, cr.country): cr for cr in session.query(ContentRating).all()}

    for rating_data in content_ratings:
        rating_key = (rating_data.get('rating'), rating_data.get('iso_3166_1'))
        if not rating_key[0] or not rating_key[1]: # skip if one is None
            logger.warning(f'error while appending new content rating to the session: {rating_key}')
            continue

        if rating_key not in existing_ratings:
            new_rating = ContentRating(rating=rating_data.get('rating'),
                                       country=rating_data.get('iso_3166_1'))
            session.add(new_rating)
            existing_ratings[rating_key] = new_rating

    return existing_ratings


def insert_production_companies(session, companies: list[dict]):
    existing_companies = {
        c.name: c for c in session.query(ProductionCompany).all()
    }

    for company in companies:
        name = company.get('name')
        if not name:
            logger.warning(f'error while appending new prod company name to the session.')
            continue

        if name not in existing_companies:
            new_company = ProductionCompany(
                id=company.get("id"),
                name=name,
                logo_path=company.get("logo_path"),
                origin_country=company.get("origin_country")
            )
            session.add(new_company)
            existing_companies[name] = new_company

    return existing_companies


def insert_networks(session, networks: list[dict]):
    existing_networks = {n.name: n for n in session.query(Network).all()}

    for network_data in networks:
        name = network_data.get('name')
        if not name:
            logger.warning(f'error while appending new network to the session.')
            continue

        if name not in existing_networks:
            new_net = Network(
                id=network_data.get("id"),
                name=name,
                logo_path=network_data.get("logo_path"),
                origin_country=network_data.get("origin_country"))
            session.add(new_net)
            existing_networks[name] = new_net

    return existing_networks


def insert_characters(session, characters: list):
    existing_characters = {c.character: c for c in session.query(Character).all()}

    for character_name in characters:    
        if character_name:
            character_name = str(character_name or None).strip() # safely convert None to '' and strip spaces

        if not character_name: # if empty after stripping
            character_name = 'NO CHARACTER' # if no character data then set it to default "NO CHARACTER" as the actor might've been a background char or special case

        character = existing_characters.get(character_name)
        if not character:
            character = Character(character=character_name)
            session.add(character)
            existing_characters[character_name] = character

    return existing_characters


def insert_actors(session, actors: list[dict]):
    existing_actors = {a.tmdb_id: a for a in session.query(Actor).all()}

    for actor_data in actors:
        tmdb_id = actor_data.get('id')
        if not tmdb_id:
            logger.warning(f'error while appending new actor to the session. actor_data -> {actor_data}')
            continue

        if tmdb_id not in existing_actors:
            new_actor = Actor(tmdb_id=actor_data.get("id"),
                              gender=actor_data.get("gender"),
                              known_for_department=actor_data.get("known_for_department"),
                              name=actor_data.get("name"),
                              original_name=actor_data.get("original_name"),
                              popularity=actor_data.get("popularity"),
                              profile_path=actor_data.get("profile_path"),
                              entry_updated=int(datetime.now(timezone.utc).timestamp()))
            session.add(new_actor)
            existing_actors[tmdb_id] = new_actor

    return existing_actors


def append_genres(session, item: MediaItem, genre_dict: dict[str, Genre], genre_names: list[str]):
    """
    Append genres to the media item if not already associated.

    How it works (explanation for myself lol): 
    1) `genre_names` is a list of genre names from freshly pulled TMDB data.
    2) `genre_dict` is a pre-fetched dictionary mapping genre names to Genre ORM objects from the database.
    3) For each name, check if it exists in `genre_dict` (if already in the DB).
    4) If the Genre object exists and is not already in `item.genres`, append it so that...
    5) SQLAlchemy will handle inserting the necessary association rows in the join table when the session is flushed or committed.

    """
    item.genres.clear()
    session.flush()

    for name in genre_names:
        genre = genre_dict.get(name)
        if genre and genre not in item.genres:
            item.genres.append(genre)


def append_content_ratings(session, item: MediaItem, ratings_dict: dict[tuple[str, str], ContentRating], ratings: list[dict]):
    """
    Append content ratings to the media item if not already associated.
    """
    item.content_ratings.clear()
    session.flush()

    existing_keys = {(cr.rating, cr.country) for cr in item.content_ratings}  # Avoid duplicates

    for rating_data in ratings:
        rating_key = (rating_data.get('rating'), rating_data.get('iso_3166_1'))

        rating = ratings_dict.get(rating_key)
        if rating and rating_key not in existing_keys:
            item.content_ratings.append(rating)
            existing_keys.add(rating_key)


def append_production_companies(session, item: MediaItem, company_dict: dict[str, ProductionCompany], companies: list[dict]):
    item.production_companies.clear()
    session.flush()

    existing_names = {c.name for c in item.production_companies}

    for company in companies:
        name = company.get('name')
        if not name or name in existing_names:
            continue

        new_company = company_dict.get(name)
        if new_company:
            item.production_companies.append(new_company)
            existing_names.add(name)


def append_networks(session, item: MediaItem, network_dict: dict[str, Network], networks: list[dict]):
    item.networks.clear()
    session.flush()

    existing_names = {n.name for n in item.networks}

    for network_data in networks:
        name = network_data.get('name')
        if not name or name in existing_names:
            continue

        new_net = network_dict.get(name)
        if new_net:
            item.networks.append(new_net)
            existing_names.add(name)


def append_videos(session, item: MediaItem, videos: list[dict]):
    item.videos.clear()
    session.flush()

    existing_videos = {video.key: video for video in item.videos}

    for video_data in videos:
        key = video_data.get('key')
        if key in existing_videos:
            # Update existing video fields
            video = existing_videos[key]
            changed = update_attrs_if_changed(video, video_data, {
                'lang': 'iso_639_1',
                'title': 'name',
                'site': 'site',
                'type': 'type',
                'official': 'official',
                'published_at': 'published_at'})
            if changed:
                video.entry_updated = int(datetime.now(timezone.utc).timestamp())

        else:
            # Add new video
            new_video = Video(
                lang=video_data.get('iso_639_1'),
                title=video_data.get('name'),
                key=key,
                site=video_data.get('site'),
                type=video_data.get('type'),
                official=video_data.get('official'),
                published_at=video_data.get('published_at'),
                entry_updated=int(datetime.now(timezone.utc).timestamp()),
                media_item=item
            )
            item.videos.append(new_video)
            session.add(new_video)


def append_logos(session, item: MediaItem, logos: list):
    item.logos.clear()
    session.flush()

    existing_logos = {logo.file_path: logo for logo in item.logos}

    for logo_data in logos:
        file_path = logo_data.get('file_path')
        if file_path in existing_logos:
            # Update existing logo fields
            logo = existing_logos[file_path]
            changed = update_attrs_if_changed(logo, logo_data, {
                'aspect_ratio': 'aspect_ratio',
                'height': 'height',
                'width': 'width',
                'lang': 'iso_639_1'})
            if changed:
                logo.entry_updated = int(datetime.now(timezone.utc).timestamp())

        else:
            # Add new logo
            new_logo = Logo(
                aspect_ratio=logo_data.get('aspect_ratio'),
                height=logo_data.get('height'),
                width=logo_data.get('width'),
                lang=logo_data.get('iso_639_1'),
                entry_updated=int(datetime.now(timezone.utc).timestamp()),
                file_path=file_path,
                media_item=item
            )
            item.logos.append(new_logo)
            session.add(new_logo)


def append_movie_details(session, item: MediaItem, data: dict):
    if item.movie_details:
        mapping = {
            'budget': 'budget',
            'revenue': 'revenue',
            'runtime': 'runtime'
        }
        updated = update_attrs_if_changed(item.movie_details, data, mapping)
        if updated:
            item.movie_details.entry_updated = int(datetime.now(timezone.utc).timestamp())

    else:
        # Insert new details
        details = MovieDetails(
            budget=data.get("budget"),
            revenue=data.get("revenue"),
            runtime=data.get("runtime"),
            entry_updated=int(datetime.now(timezone.utc).timestamp()),
            media_item=item)
        
        session.add(details)
        item.movie_details = details


def append_tv_details(session, item: MediaItem, data: dict):
    if item.tv_details:
        mapping = {
            'first_air_date': 'first_air_date',
            'last_air_date': 'last_air_date',
            'number_of_episodes': 'number_of_episodes',
            'number_of_seasons': 'number_of_seasons',
        }
        updated = update_attrs_if_changed(item.tv_details, data, mapping)
        if updated:
            item.tv_details.entry_updated = int(datetime.now(timezone.utc).timestamp())

    else:
        # Insert new details
        details = TvDetails(
            first_air_date=data.get("first_air_date"),
            last_air_date=data.get("last_air_date"),
            number_of_episodes=data.get("number_of_episodes"),
            number_of_seasons=data.get("number_of_seasons"),
            entry_updated=int(datetime.now(timezone.utc).timestamp()),
            media_item=item)
        
        session.add(details)
        item.tv_details = details  # ensures the ORM links both ways


def append_tv_season(session, media_item: MediaItem, season_data: dict) -> TvSeason:
    season_number = season_data.get("season_number")

    if not media_item.tv_details:
        media_item.tv_details = TvDetails(media_item=media_item)
        session.add(media_item.tv_details)


    existing = next((s for s in media_item.tv_details.seasons if s.season_number == season_number), None)
    if existing:
        mapping = {
            'tmdb_season_id': 'id',
            'air_date': 'air_date',
            'name': 'name',
            'overview': 'overview',
            'poster_path': 'poster_path',
        }
        updated = update_attrs_if_changed(existing, season_data, mapping)

        # handle episode_count
        if 'episodes' in season_data:
            new_count = len(season_data['episodes'])
            if existing.episode_count != new_count:
                existing.episode_count = new_count
                updated = True

        if updated:
            existing.entry_updated = int(datetime.now(timezone.utc).timestamp())

        return existing

    # Create new season if not found
    new_season = TvSeason(
        tmdb_season_id=season_data.get("id"),
        season_number=season_number,
        air_date=season_data.get("air_date"),
        episode_count=len(season_data.get('episodes', [])) if season_data.get('episodes') else None,
        name=season_data.get("name"),
        overview=season_data.get("overview"),
        poster_path=season_data.get("poster_path"),
        entry_updated=int(datetime.now(timezone.utc).timestamp()),
        tv_details=media_item.tv_details,
        media_id=media_item.id
    )

    session.add(new_season)
    media_item.tv_details.seasons.append(new_season)

    return new_season


def append_tv_episode(session, season: TvSeason, episode_data: dict):
    episode_number = episode_data.get("episode_number")

    existing = next((e for e in season.episodes if e.episode_number == episode_number), None)

    if existing:
        mapping = {
            'tmdb_episode_id': 'id',
            'season_number': 'season_number',
            'name': 'name',
            'overview': 'overview',
            'air_date': 'air_date',
            'still_path': 'still_path',
            'runtime': 'runtime',
            'episode_type': 'episode_type',
            'vote_average': 'vote_average',
            'vote_count': 'vote_count'
        }
        updated = update_attrs_if_changed(existing, episode_data, mapping)
        if updated:
            existing.entry_updated = int(datetime.now(timezone.utc).timestamp())

        return existing

    # Create new episode
    new_episode = TvEpisode(
        tmdb_episode_id=episode_data.get('id'),
        season_number=episode_data.get("season_number"),
        episode_number=episode_number,
        name=episode_data.get("name"),
        overview=episode_data.get("overview"),
        air_date=episode_data.get("air_date"),
        still_path=episode_data.get("still_path"),
        runtime=episode_data.get("runtime"),
        episode_type=episode_data.get("episode_type"),
        vote_average=episode_data.get("vote_average"),
        vote_count=episode_data.get("vote_count"),
        entry_updated=int(datetime.now(timezone.utc).timestamp()),
        media_id=season.media_id,
        tv_season=season
    )

    session.add(new_episode)
    season.episodes.append(new_episode)

    return new_episode


def append_cast(session, item: MediaItem, existing_characters: dict[str, Character], existing_actors: dict[str, Actor], cast_data: list[dict], clear_existing: bool = True):
    if clear_existing:
        for mc in list(item.media_cast):
            session.delete(mc)
        session.flush()
        existing_cast = {}
    else:
        # Map existing cast_data entries on this media item
        existing_cast = {(mc.actor_id, mc.character_id): mc for mc in item.media_cast}

    for entry in cast_data:
        actor_tmdb_id = entry.get('id')
        character_name = entry.get('character')
        episode_count = entry.get('episode_count')

        # Normalize character name
        if character_name:
            character_name = str(character_name or '').strip()
        if not character_name:
            character_name = 'NO CHARACTER'

        actor_obj = existing_actors.get(actor_tmdb_id)
        character_obj = existing_characters.get(character_name)

        if not actor_obj or not character_obj:
            logger.warning(f"skipping invalid actor/character ({actor_obj}/{character_obj})")
            continue

        key = (actor_obj.id, character_obj.id)

        if key in existing_cast:
            # Update existing cast entry if needed
            mc = existing_cast[key]
            if mc.episode_count != episode_count:
                mc.episode_count = episode_count
                session.add(mc)
        else:
            # Insert new cast entry
            new_cast = MediaCast(
                media_item=item,
                actor_id=actor_obj.id,
                character_id=character_obj.id,
                episode_count=episode_count,
                entry_updated=int(datetime.now(timezone.utc).timestamp())
            )
            item.media_cast.append(new_cast)
            session.add(new_cast)






def insert_new(data: dict):
    """
    Returns that row id.
    """
    with Session() as session:
        item = MediaItem(title=data['title'], release_date=data['release_date'], media_type=data['media_type'], hash_key=data['hash_key'], entry_created=int(datetime.now(timezone.utc).timestamp()))
        session.add(item)
        session.commit()
        id = item.id

    logger.info(f"successfully inserted: '{data.get('media_type')}', '{data.get('title')}' (ID {id})")
    return id


def insert_video_file(id, data: dict):
    """
    returns row id for video in media_metadata table
    """
    with Session() as session:
        item = session.query(MediaItem).filter_by(id=id).one_or_none()
        if not item:
            logger.debug(f'error, item ({id}) not found in database')
            return
        
        video = VideoMetadata(
            media_id=item.id,
            season_number=data.get('season_number'),
            episode_number=data.get('episode_number'),
            file_path=data.get('file_path'),
            hash_key=data.get('hash_key'),
            keyframe_path=data.get('key_frame'),

            resolution=data.get('resolution'),
            extension=data.get('extension'),
            audio_codec=data.get('audio_codec'),
            video_codec=data.get('video_codec'),
            size=data.get('size'),
            bitrate=data.get('bitrate'),
            duration=data.get('duration'),
            frame_rate=data.get('frame_rate'),
            width=data.get('width'),
            height=data.get('height'),
            aspect_ratio=data.get('aspect_ratio'),
            entry_updated=int(datetime.now(timezone.utc).timestamp())
            )
        item.media_metadata.append(video)
        item.new_video_inserted = int(datetime.now(timezone.utc).timestamp())
        session.commit()
        video_id = video.id

    return video_id


def insert_subtitles(video_id, subtitles: list[dict]):
    """
    video_id = row id for video in media_metadata
    """
    with Session() as session:
        video = session.query(VideoMetadata).filter_by(id=video_id).first()
        for subtitle_data in subtitles:
            if not subtitle_data.get('path'):
                logger.debug(f'subtitle path not found. video: {video_id}')
                continue

            subtitle = Subtitle(
                media_id=video.media_id,
                media_metadata=video,
                lang=subtitle_data.get('lang'),
                label=subtitle_data.get('label'),

                file_path=subtitle_data.get('path'),
                hash_key=subtitle_data.get('hash_key'),

                entry_updated=int(datetime.now(timezone.utc).timestamp())
                )
            session.add(subtitle)
        session.commit()


def update_id(id, data: dict):
    logger.info(f"Updating: '{data.get('media_type')}', '{data.get('title')}'... (ID {id})")
    with Session() as session:
        item = session.query(MediaItem).filter_by(id=id).one_or_none()
        if not item:
            logger.warning(f'update failed, item ({id}) not found in database')
            return  


        existing_genres = insert_genres(session, data.get('genres', []))
        existing_content_ratings = insert_content_ratings(session, data.get('content_ratings', []))
        existing_production_companies = insert_production_companies(session, data.get('production_companies', []))
        existing_networks = insert_networks(session, data.get('networks', []))
        existing_characters = insert_characters(session, [cast.get('character') for cast in data.get('cast',[])]) 
        existing_actors = insert_actors(session, data.get('cast',[]))

        upsert_item(item, data)

        append_genres(session, item, existing_genres, data.get('genres', []))
        append_content_ratings(session, item, existing_content_ratings, data.get('content_ratings', []))
        append_production_companies(session, item, existing_production_companies, data.get('production_companies', []))
        append_networks(session, item, existing_networks, data.get('networks', []))
        append_videos(session, item, data.get('videos', []))
        append_logos(session, item, data.get('logos', []))
        append_cast(session, item, existing_characters, existing_actors, data.get('cast', []))


        if item.media_type == MediaType.MOVIE:
            append_movie_details(session, item, data)
        elif item.media_type == MediaType.TV:
            append_tv_details(session, item, data)

            for season_data in data.get('seasons', []):
                tv_season = append_tv_season(session, item, season_data)

                for episode_data in season_data.get("episodes", []):
                    append_tv_episode(session, tv_season, episode_data)


        if last_updated_flag:
            item.entry_updated = int(datetime.now(timezone.utc).timestamp())

        session.commit()
        logger.info(f"Successfully updated: '{data.get('media_type')}', '{data.get('title')}'. (ID {id})")


def delete_metadata_videos(missing_video_hashes: list):
    with Session() as session:
        for hash_key in missing_video_hashes:
            video = session.query(VideoMetadata).filter_by(hash_key=hash_key).one_or_none()
            if video:
                session.delete(video)
        session.commit()





def insert_new_user(password: str, key: str, is_admin=False, is_adult=True):
    logger.info(f"Creating new user account...")
    if not (password and isinstance(password, str)) or not (key and isinstance(key, str)):
        logger.warning("user account creation failed: invalid password or key format.")
        return
    
    if not isinstance(is_admin, bool) or not isinstance(is_adult, bool):
        logger.warning("user account creation failed: is_admin or is_adult format.")
        return
    
    with Session() as session:
        random_name = f'#{randint(0, 9999):04}'
        default_picture = 'default_profile.jpg'
        entry_created = int(datetime.now(timezone.utc).timestamp())

        user = User(
            password=password,
            key=key,
            is_adult=is_adult,
            is_admin=is_admin,
            entry_created=entry_created,
            entry_updated=entry_created
        )

        profile = UserProfile(
            profile_name=random_name,
            profile_picture=default_picture,
            entry_created=entry_created,
            entry_updated=entry_created
        )

        user.user_profile = profile

        session.add(user)
        session.commit()

    logger.info("New user account created successfully.")


class DB():
    @staticmethod
    def fetch_catalog_index():
        with Session() as session:
            items = session.query(MediaItem.id, MediaItem.title, MediaItem.media_type).all()
        return items
    
    @staticmethod
    def fetch_catalog(order_by='entry_updated', order_=desc, limit=20, media_type=None):
        """
        Fetch a list of MediaItem entries from the database, ordered and limited.

        Args:
            order_by (str): The field/column name to order the results by. Default is "entry_updated".
                            Example values: "title", "entry_updated"
            order_ (function): SQLAlchemy ordering function: desc (default) or asc.
            limit (int): Maximum number of results to return. Default is 20.
            media_type (str): 'tv' | 'movie'
        Returns:
            List[MediaItem]: A list of MediaItem objects.
        """

        with Session() as session:
            # Get the column object by name
            column = getattr(MediaItem, order_by, None)
            if column is None:
                raise ValueError(f"Invalid column name: '{order_by}'")

            if media_type:
                items = (
                    session.query(MediaItem)
                    .filter_by(media_type=media_type)
                    .order_by(order_(column))
                    .limit(limit)
                    .all()
                )
            else:
                items = (
                    session.query(MediaItem)
                    .order_by(order_(column))
                    .limit(limit)
                    .all()
                )

        return items


    @staticmethod
    def fetch_id(id):
        with Session() as session:
            item = session.query(MediaItem).filter_by(id=id).options(joinedload(MediaItem.genres), joinedload(MediaItem.logos)).one_or_none()
        return item


    @staticmethod
    def fetch_tv_details(id):
        with Session() as session:
            item = session.query(MediaItem).filter_by(id=id).options(joinedload(MediaItem.tv_details)).one_or_none()
        return item


    @staticmethod
    def fetch_movie_details(id):
        with Session() as session:
            item = session.query(MediaItem).filter_by(id=id).options(joinedload(MediaItem.movie_details)).one_or_none()
        return item
    

    @staticmethod
    def fetch_genres(id):
        with Session() as session:
            item = session.query(MediaItem).filter_by(id=id).options(joinedload(MediaItem.genres)).one_or_none()
            return item.genres if item else []


    @staticmethod
    def fetch_cast(id):
        with Session() as session:
            item = session.query(MediaItem).filter_by(id=id).options(
                joinedload(MediaItem.media_cast).joinedload(MediaCast.actor),
                joinedload(MediaItem.media_cast).joinedload(MediaCast.character)
            ).one_or_none()
            return item.media_cast if item else []


    @staticmethod
    def fetch_trailers(id):
        with Session() as session:
            item = session.query(MediaItem).filter_by(id=id).options(joinedload(MediaItem.videos)).one_or_none()
            return item.videos if item else []


    @staticmethod
    def fetch_networks(id):
        with Session() as session:
            item = session.query(MediaItem).filter_by(id=id).options(joinedload(MediaItem.networks)).one_or_none()
            return item.networks if item else []


    @staticmethod
    def fetch_ratings(id):
        with Session() as session:
            item = session.query(MediaItem).filter_by(id=id).options(joinedload(MediaItem.content_ratings)).one_or_none()
            return item.content_ratings if item else []


    @staticmethod
    def fetch_season(id):
        with Session() as session:
            item = session.query(MediaItem).filter_by(id=id).options(joinedload(MediaItem.tv_details).joinedload(TvDetails.seasons).joinedload(TvSeason.episodes)).one_or_none()
            return item.tv_details.seasons if item and item.tv_details else []


    @staticmethod
    def fetch_episodes(id):
        with Session() as session:
            item = session.query(MediaItem).filter_by(id=id).options(joinedload(MediaItem.tv_details).joinedload(TvDetails.seasons).joinedload(TvSeason.episodes)).one_or_none()
            if not item or not item.tv_details:
                return []
            return [ep for season in item.tv_details.seasons for ep in season.episodes]


    @staticmethod
    def fetch_episode(id: int, season_number: int, episode_number: int):
        with Session() as session:
            item = session.query(MediaItem).filter_by(id=id).options(
                joinedload(MediaItem.tv_details)
                .joinedload(TvDetails.seasons)
                .joinedload(TvSeason.episodes)
            ).one_or_none()

            if not item or not item.tv_details:
                return None

            for season in item.tv_details.seasons:
                if season.season_number == season_number:
                    for episode in season.episodes:
                        if episode.episode_number == episode_number:
                            return episode
            return None


    @staticmethod
    def fetch_videos(id):
        with Session() as session:
            item = session.query(MediaItem).filter_by(id=id).options(joinedload(MediaItem.media_metadata).joinedload(VideoMetadata.subtitles)).one_or_none()
        return item.media_metadata


    @staticmethod
    def fetch_video(video_id):
        with Session() as session:
            item = session.query(VideoMetadata).filter_by(id=video_id).options(joinedload(VideoMetadata.subtitles)).one_or_none()
        return item        

    @staticmethod
    def fetch_video_by_hash(key):
        with Session() as session:
            video = session.query(VideoMetadata).filter_by(hash_key=key).options(joinedload(VideoMetadata.subtitles)).one_or_none()
        return video


    @staticmethod
    def fetch_subtitles(video_id):
        with Session() as session:
            subtitles = session.query(Subtitle).filter_by(video_id=video_id).all()
            return subtitles if subtitles else []        


    @staticmethod
    def fetch_subtitle_by_hash(key):
        with Session() as session:
            subtitle = session.query(Subtitle).filter_by(hash_key=key).one_or_none()
            return subtitle 


    @staticmethod
    def fetch_catalog_by_genre(genre_name: str):
        with Session() as session:
            genre = session.query(Genre).options(joinedload(Genre.media_item)).filter_by(name=genre_name).first()

            if genre:
                return genre.media_item  # This will be a list of MediaItem objects
            return []
    

    @staticmethod
    def fetch_hash_MediaItem():
        with Session() as session:
            hashes = session.query(MediaItem.hash_key).all()
        return [h[0] for h in hashes]


    @staticmethod
    def fetch_hash_VideoMetadata():
        with Session() as session:
            hashes = session.query(VideoMetadata.hash_key).all()
        return [h[0] for h in hashes]


    @staticmethod
    def fetch_by_hash_key(key):
        with Session() as session:
            item = session.query(MediaItem).filter_by(hash_key=key).one_or_none()
        return item

    @staticmethod
    def search(input_str):
        """
        Search for media items where the title matches `input_str`.

        Returns item obj.
        """
        with Session() as session:
            items = (
                session.query(MediaItem)
                .options(joinedload(MediaItem.genres))
                .filter(MediaItem.title.ilike(f"%{input_str}%"))
                .all()
            )
            return items


    @staticmethod
    def fetch_users():
        with Session() as session:
            users = session.query(User).all()
        return [{'hash': user.password, 'key': user.key, 'is_admin': user.is_admin, 'is_adult': user.is_adult} for user in users]


    @staticmethod
    def fetch_user(key):
        with Session() as session:
            user = session.query(User).filter_by(key=key).options(
                joinedload(User.user_profile), 
                joinedload(User.user_library), 
                joinedload(User.user_playback)
            ).one_or_none()
        return user


    @staticmethod
    def set_user_playback(key: str, data: dict):
        media_id = data.get('media_id')
        video_id = data.get('video_id')
        video_paused_at = data.get('video_paused_at', 0)
        seconds_played = data.get('seconds_played', 0)
        is_watched = data.get('watched', False)
        video_duration = data.get('video_duration', 0)

        if not all([key, data, data.get('media_id'), data.get('video_id')]):
            logger.warning(f'failed to update user playback. (user: {key}, data: {data})')


        with Session() as session:
            user = session.query(User).filter_by(key=key).options(joinedload(User.user_playback)).one_or_none()

            # Find existing playback for this user/media/video combo
            playback = None
            for p in user.user_playback:
                if p.video_id == video_id and p.media_id == media_id:
                    playback = p
                    break

            now_ts = int(datetime.utcnow().timestamp())

            if playback:
                # Update existing record
                playback.watched = is_watched 
                playback.paused_at = video_paused_at
                playback.watchtime = playback.watchtime + seconds_played if seconds_played != 0 else playback.watchtime_total
                playback.entry_updated = now_ts
            else:
                # Create new UserPlayback record
                playback = UserPlayback(
                    user_key=user.key,
                    media_id=media_id,
                    video_id=video_id,
                    watched=is_watched,
                    paused_at=video_paused_at,
                    video_duration = video_duration,
                    watchtime=video_paused_at,
                    entry_created=now_ts,
                    entry_updated=now_ts,
                    user=user
                )
                session.add(playback)

            session.commit()


    @staticmethod
    def set_user_library(key: str, data: dict):
        media_id = data.get('media_id')
        watchlisted = data.get('watchlisted')
        rated = data.get('rated')

        with Session() as session:
            user = session.query(User).filter_by(key=key).options(joinedload(User.user_library)).one_or_none()

            

            library_item = None
            for l in user.user_library:
                if l.media_id == media_id:
                    library_item = l
                    break

            now_ts = int(datetime.utcnow().timestamp())

            if library_item:
                # Update existing record
                library_item.rated = rated  if rated is not None else library_item.rated
                library_item.watchlisted = watchlisted if watchlisted is not None else library_item.watchlisted
                library_item.entry_updated = now_ts
            else:
                # Create new
                library_item = UserLibrary(
                    user_key=user.key,
                    media_id=media_id,
                    rated=rated,
                    watchlisted=watchlisted,
                    entry_created=now_ts,
                    entry_updated=now_ts,
                    user=user
                )
                session.add(library_item)

            session.commit()


    @staticmethod
    def delete_media_item(id: int):
        """
        Delete row from main table 'media_items' with specified Id.
        """

        with Session() as session:
            item = session.get(MediaItem, id)

            if item:
                session.delete(item)
                session.commit()            


    @staticmethod
    def delete_video(id: int):
        """
        Delete row from metadata table 'media_metadata' with specified Id.
        """

        with Session() as session:
            item = session.get(VideoMetadata, id)

            if item:
                session.delete(item)
                session.commit()   


    @staticmethod
    def delete_user(key: str):
        """
        Delete row from main table 'media_items' with specified Id.
        """

        with Session() as session:
            item = session.get(User, key)

            if item:
                session.delete(item)
                session.commit()    







if __name__ == "__main__":
    create_localdb()

     