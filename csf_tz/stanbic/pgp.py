import pgpy


def encrypt_pgp(message, key):
	"""Encrypt a message with a public key"""
	key, _ = pgpy.PGPKey.from_blob(key)
	message = pgpy.PGPMessage.new(message)
	message |= key.pubkey.encrypt(message)
	return str(message)
