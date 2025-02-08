from sqlalchemy import create_engine, Column, Integer, String
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
    url = Column(String, nullable=True)  # Последняя отправленная ссылка
    title = Column(String, nullable=True) # Последнее название файла

# Создаем таблицы
Base.metadata.create_all(bind=engine)

# Получение сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Получить пользователя по user_id
def get_user(db, user_id):
    return db.query(User).filter(User.user_id == user_id).first()

# Создать нового пользователя или обновить URL
def update_or_create_user(db, user_id, url, title):
    user = get_user(db, user_id)
    if user:
        user.url = url  # Обновляем URL
        user.title = title
    else:
        user = User(user_id=user_id, url=url, title=title)  # Создаем нового пользователя
        db.add(user)
    db.commit()

