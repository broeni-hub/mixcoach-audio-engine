from sqlalchemy import Column, Float, Integer, JSON, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TrackAnalysisDB(Base):
    __tablename__ = "track_analysis"

    id = Column(Integer, primary_key=True)

    filename = Column(String, unique=True, nullable=False)

    duration = Column(Float)
    tempo = Column(Float)

    musical_key = Column(String)
    camelot = Column(String)

    analysis = Column(JSON)