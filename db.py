from sqlalchemy import create_engine, Column, Integer, String, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Настройка базы данных
Base = declarative_base()
engine = create_engine('sqlite:///bot_data.db')  # SQLite файл
SessionLocal = sessionmaker(bind=engine)

# Модель пользователя
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True)  # Telegram user_id
    video_id = Column(Integer, unique=True, index=True) # id видео из источника
    url = Column(String, nullable=True)  # Последняя отправленная ссылка
    title = Column(String, nullable=True) # Последнее название файла
    resolutions = Column(String, nullable=True)  # Расширение
    telegram_id = Column(Integer, unique=True, index=True, nullable=True)  # id видео из источника

# Создаем таблицы
Base.metadata.create_all(bind=engine)


def get_db():
    """
        Инициализирует сессию базы данных.

        """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user(db, user_id):
    """
        Осуществляет поиск пользователя по базе данных.

        Args:
            user_id (int): id пользователя из телеграмма

        Returns:
            int: первую строку id пользователя из базы данных.
        """
    return db.query(User).filter(User.user_id == user_id).first()

def update_or_create_user(db, user_id, url, video_id, title):
    """
        Создает или обновляет данные пользователя в базе данных.

        Args:
           user_id  (int): уникальный id пользователя из телеграмма
           url      (str): ссылка на файл
           video_id (str): уникальный id видео из источника
           title    (str): название файла из источника
        """
    user = get_user(db, user_id)
    if user:
        user.url = url
        user.title = title
        user.video_id = video_id
    else:
        user = User(user_id=user_id, url=url, video_id=video_id, title=title)  # Создаем нового пользователя
        db.add(user)
    db.commit()

def count_users(db: Session):
    return db.query(func.count(User.id)).scalar()




