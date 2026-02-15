import pgpy


def encrypt_pgp(message: str, public_key: str) -> str:
    """Encrypt a message with a public key."""
    key, _ = pgpy.PGPKey.from_blob(public_key)
    msg = pgpy.PGPMessage.new(message)
    msg |= key.pubkey.encrypt(msg)
    return str(msg)
