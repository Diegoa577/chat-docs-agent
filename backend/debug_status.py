from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Base, ChunkModel, DocumentModel

engine = create_engine('postgresql://cda_user:cda_password@localhost:5432/cda_test_db', echo=False, future=True)
Base.metadata.create_all(bind=engine)
with Session(engine) as s:
    doc = DocumentModel(id=uuid4(), filename='t.txt', content_type='text/plain', status='completed')
    s.add(doc)
    s.flush()
    chunk = ChunkModel(document_id=doc.id, content=' Inclusion criteria: adult patients.', chunk_index=0, embedding=[0.1]*384)
    s.add(chunk)
    s.commit()
    print('after commit doc status', doc.status)
    doc.status = "processing"  # type: ignore[assignment]
    s.commit()
    print('after update status', doc.status)
    cnt = s.execute(text("SELECT COUNT(*) FROM chunks c JOIN documents d ON c.document_id=d.id WHERE d.status='completed'")).scalar()
    print('completed chunks count', cnt)
