from app.auth.hashing import hash_secret, verify_secret


def test_hash_is_not_the_plaintext() -> None:
    assert hash_secret("correct horse battery staple") != "correct horse battery staple"


def test_verify_accepts_the_right_secret() -> None:
    hashed = hash_secret("s3cret")
    assert verify_secret("s3cret", hashed) is True


def test_verify_rejects_the_wrong_secret() -> None:
    hashed = hash_secret("s3cret")
    assert verify_secret("wrong", hashed) is False


def test_hashes_of_the_same_secret_differ() -> None:
    assert hash_secret("same") != hash_secret("same")
