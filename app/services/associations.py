from sqlmodel import Session, select

from app.models import Association


def get_or_create_association(db: Session, name: str) -> Association:
    """Find an association by name, or create one."""
    existing = db.exec(
        select(Association).where(Association.name == name)
    ).one_or_none()
    if existing is not None:
        return existing
    association = Association(name=name)
    db.add(association)
    db.commit()
    db.refresh(association)
    return association
