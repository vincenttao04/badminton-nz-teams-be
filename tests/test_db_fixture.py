from sqlmodel import Session, select

from app.models import Association


def test_db_session_can_write_and_read(db_session: Session) -> None:
    db_session.add(Association(name="Test Association"))
    db_session.commit()
    found = db_session.exec(
        select(Association).where(Association.name == "Test Association")
    ).one()
    assert found.id is not None


def test_db_session_is_isolated_between_tests(db_session: Session) -> None:
    # Same name as the test above; passes only because each test starts clean.
    db_session.add(Association(name="Test Association"))
    db_session.commit()
    found = db_session.exec(
        select(Association).where(Association.name == "Test Association")
    ).all()
    assert len(found) == 1
