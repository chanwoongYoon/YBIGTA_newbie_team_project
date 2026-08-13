from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mcp_server.config import DATABASE_URL

# pool_pre_ping avoids handing out dead connections after RDS idle-timeouts.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
