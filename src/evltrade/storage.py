from datetime import datetime
from sqlalchemy import Boolean,DateTime,Integer,String,Text,Numeric,create_engine,ForeignKey
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,sessionmaker

class Base(DeclarativeBase): pass

class ExperimentRecord(Base):
    __tablename__='experiments'
    id:Mapped[str]=mapped_column(String(32),primary_key=True)
    dataset_id:Mapped[str]=mapped_column(String(128),nullable=False)
    strategy_id:Mapped[str]=mapped_column(String(128),nullable=False)
    engine_version:Mapped[str]=mapped_column(String(32),nullable=False)
    seed:Mapped[int]=mapped_column(Integer,nullable=False)
    initial_capital:Mapped[float]=mapped_column(Numeric(20,8),nullable=False,default=1000)
    immutable:Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,nullable=False)
    assumptions_json:Mapped[str]=mapped_column(Text,default='{}')

class StrategyRecord(Base):
    __tablename__='strategies'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    name:Mapped[str]=mapped_column(String(200),nullable=False)
    version:Mapped[int]=mapped_column(Integer,nullable=False,default=1)
    genome_hash:Mapped[str]=mapped_column(String(128),nullable=False,index=True)
    genome_json:Mapped[str]=mapped_column(Text,nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime,nullable=False)

class DatasetRecord(Base):
    __tablename__='datasets'
    id:Mapped[str]=mapped_column(String(128),primary_key=True)
    source:Mapped[str]=mapped_column(String(300),nullable=False)
    version:Mapped[str]=mapped_column(String(100),nullable=False)
    symbol:Mapped[str]=mapped_column(String(80),nullable=False)
    timeframe:Mapped[str]=mapped_column(String(40),nullable=False)
    timezone:Mapped[str]=mapped_column(String(80),nullable=False)
    quality:Mapped[str]=mapped_column(String(30),nullable=False)
    content_hash:Mapped[str]=mapped_column(String(128),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime,nullable=False)

class RunRecord(Base):
    __tablename__='runs'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    kind:Mapped[str]=mapped_column(String(40),nullable=False)
    status:Mapped[str]=mapped_column(String(30),nullable=False)
    progress:Mapped[float]=mapped_column(Numeric(8,5),default=0)
    seed:Mapped[int]=mapped_column(Integer,nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime,nullable=False)
    config_json:Mapped[str]=mapped_column(Text,default='{}')

class PortfolioRecord(Base):
    __tablename__='portfolios'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    cash:Mapped[float]=mapped_column(Numeric(20,8),default=1000)
    equity:Mapped[float]=mapped_column(Numeric(20,8),default=1000)
    drawdown:Mapped[float]=mapped_column(Numeric(12,8),default=0)

class TradeRecord(Base):
    __tablename__='trades'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    experiment_id:Mapped[str]=mapped_column(String(32),ForeignKey('experiments.id'),nullable=False,index=True)
    strategy_id:Mapped[str]=mapped_column(String(128),nullable=False)
    symbol:Mapped[str]=mapped_column(String(80),nullable=False)
    side:Mapped[str]=mapped_column(String(8),nullable=False)
    price:Mapped[float]=mapped_column(Numeric(30,12),nullable=False)
    quantity:Mapped[float]=mapped_column(Numeric(30,12),nullable=False)
    fee:Mapped[float]=mapped_column(Numeric(20,8),default=0)
    created_at:Mapped[datetime]=mapped_column(DateTime,nullable=False)

class LineageRecord(Base):
    __tablename__='lineage'
    child_id:Mapped[str]=mapped_column(String(80),primary_key=True)
    parent_ids_json:Mapped[str]=mapped_column(Text,nullable=False)
    generation:Mapped[int]=mapped_column(Integer,nullable=False)
    operation:Mapped[str]=mapped_column(String(80),nullable=False)
    genome_hash:Mapped[str]=mapped_column(String(128),nullable=False)


def session_factory(url='sqlite:///./evoltrade.db'):
    engine=create_engine(url,future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine,expire_on_commit=False)
