from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from database import engine  # Где создан SQLAlchemy engine

Base = declarative_base()


# Определение модели User
class User(Base):
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    api = Column(String, unique=True, nullable=True)
    yt_count = Column(BigInteger, nullable=True)
    tt_count = Column(BigInteger, nullable=True)
    vk_count = Column(BigInteger, nullable=True)
    subscribes_count = Column(BigInteger, nullable=True)
    status_api = Column(Boolean, default=False)
    login_time = Column(DateTime, default=datetime.utcnow)
    last_enter_date = Column(DateTime, default=datetime.utcnow)

    subscribes = relationship("Subscribe", back_populates="user", cascade="all, delete-orphan")
    playlists = relationship("Playlist", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"

class Channel(Base):
    __tablename__ = 'channels'

    channel_id = Column(String, primary_key=True)  # Теперь основной ключ
    channel_name = Column(String, nullable=True)
    channel_avatar = Column(String, nullable=True)
    subscribers_count = Column(String, nullable=True)
    video_count = Column(String, nullable=True)

    subscribes = relationship("Subscribe", back_populates="channel")
    videos = relationship("Video", back_populates="channel", cascade="all, delete-orphan")

class Subscribe(Base):
    __tablename__ = 'subscribes'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    channel_id = Column(String, ForeignKey('channels.channel_id'), nullable=False)  # Всё правильно
    status = Column(Boolean, default=True, nullable=False)  # Добавлено поле статус

    user = relationship("User", back_populates="subscribes")
    channel = relationship("Channel", back_populates="subscribes")

class Playlist(Base):
    __tablename__ = 'playlists'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))


    user = relationship("User", back_populates="playlists")
    files = relationship("File", back_populates="playlist", cascade="all, delete-orphan")

class Video(Base):
    __tablename__ = 'videos'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    youtube_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    author = Column(String, nullable=True)
    thumbnail = Column(String, nullable=True)
    url = Column(String, nullable=False)
    channel_id = Column(String, ForeignKey('channels.channel_id', ondelete="CASCADE"), nullable=False)
    time = Column(BigInteger, nullable=True)
    date = Column(String, nullable=True)

    channel = relationship("Channel", back_populates="videos")
    files = relationship("File", back_populates="video", cascade="all, delete-orphan")

class Info(Base):
    __tablename__ = 'infos'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_id = Column(BigInteger, ForeignKey('videos.id', ondelete="CASCADE"), nullable=False)
    format_id = Column(String, nullable=False)
    type = Column(String, default='Video')
    resolution = Column(String, nullable=True)
    size = Column(String, nullable=True)
    status = Column(Boolean, default=False)

    files = relationship("File", back_populates="info")

class File(Base):
    __tablename__ = "files"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_id = Column(BigInteger, ForeignKey('videos.id'), nullable=False)
    format_id = Column(BigInteger, ForeignKey('infos.id'), nullable=False)
    playlist_id = Column(BigInteger, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=True)
    id_telegram = Column(String, nullable=True)

    playlist = relationship("Playlist", back_populates="files")
    video = relationship("Video", back_populates="files")
    info = relationship("Info", back_populates="files")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)