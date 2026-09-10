from datetime import datetime
from sqlalchemy import Boolean,DateTime,Integer,String,Text,Numeric,create_engine
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,sessionmaker
class Base(DeclarativeBase): pass
class ExperimentRecord(Base):
 __tablename__='experiments'
 id:Mapped[str]=mapped_column(String(32),primary_key=True); dataset_id:Mapped[str]=mapped_column(String(128),nullable=False); strategy_id:Mapped[str]=mapped_column(String(128),nullable=False); engine_version:Mapped[str]=mapped_column(String(32),nullable=False); seed:Mapped[int]=mapped_column(Integer,nullable=False); initial_capital:Mapped[float]=mapped_column(Numeric(20,8),nullable=False,default=1000); immutable:Mapped[bool]=mapped_column(Boolean,nullable=False,default=True); created_at:Mapped[datetime]=mapped_column(DateTime,nullable=False); assumptions_json:Mapped[str]=mapped_column(Text,default='{}')
def session_factory(url='sqlite:///./evoltrade.db'):
 engine=create_engine(url,future=True); Base.metadata.create_all(engine); return sessionmaker(engine,expire_on_commit=False)
