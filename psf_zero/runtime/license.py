import os
import hmac
import hashlib
import base64
import logging

# Secret known ONLY to the issuer (server-side). Not required on the client side.
# In the client's environment, this remains an empty string and only verification occurs.
SECRET = os.getenv("PSF_ZERO_LICENSE_SECRET", "")

def generate_license_key(feature: str) -> str:
    """ For Issuers: Generates a license key for a specific feature. """
    if not SECRET:
        raise ValueError("PSF_ZERO_LICENSE_SECRET must be set to generate keys.")
    sig = hmac.new(SECRET.encode(), msg=feature.encode(), digestmod=hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode()[:24]

def verify_license(license_key: str, feature: str) -> bool:
    """ For Users: Verifies if the provided key unlocks the requested feature. """
    if not license_key:
        return False
    
    # Pseudo-local verification (For commercial production, replacing this with Asymmetric Public Key Crypto is recommended).
    # This is a conceptual implementation matching the environment variable key with the expected hash.
    expected_sig = hmac.new(feature.encode(), msg=feature.encode(), digestmod=hashlib.sha256).digest()
    expected_key = base64.urlsafe_b64encode(expected_sig).decode()[:24]
    
    # In a real-world scenario, you would use JWT or Ed25519 public keys for "offline verification".
    # Here, we verify if the user injected the correct string into PSF_ZERO_LICENSE_KEY.
    is_valid = hmac.compare_digest(expected_key, license_key[:24])
    
    if is_valid:
        logging.info(f"[PSF-Zero Pro] Feature unlocked: {feature}")
    
    return is_valid
