import os
import base64
from nacl.public import PrivateKey


def generate_keys():
    """Generates a pair of public and private keys and saves them to the files"""
    keys_dir = "keys"
    private_key_path = os.path.join(keys_dir, "private_key.key")
    public_key_path = os.path.join(keys_dir, "public_key.key")

    # Check if keys already exist
    if os.path.exists(private_key_path) and os.path.exists(public_key_path):
        return

    os.makedirs(keys_dir, exist_ok=True)

    private_key = PrivateKey.generate()
    public_key = private_key.public_key

    with open(private_key_path, "wb") as f:
        f.write(base64.b64encode(private_key.encode()))

    with open(public_key_path, "wb") as f:
        f.write(base64.b64encode(public_key.encode()))

if __name__ == "__main__":
    generate_keys()
