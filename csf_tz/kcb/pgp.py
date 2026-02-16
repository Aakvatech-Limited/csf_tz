import pgpy


def encrypt_pgp(message: str | bytes, public_key: str) -> str:
    """Encrypt a message with a public key."""
    key, _ = pgpy.PGPKey.from_blob(public_key)

    if isinstance(message, bytes):
        msg = pgpy.PGPMessage.new(message, file=True)
    else:
        msg = pgpy.PGPMessage.new(message)

    encrypted = key.pubkey.encrypt(msg)
    return str(encrypted)
