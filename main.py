from uv import Uv
from db.models import Base
from db.database import engine
from api import document

app = Uv()
Base.metadata.create_all(bind=engine)

app.include_router(document.router, prefix="/document")