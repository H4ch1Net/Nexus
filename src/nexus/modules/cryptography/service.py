from __future__ import annotations
import math
import re
import string
from collections import Counter
from typing import Dict, List, Tuple

# Character sets for various encodings
BASE16_CHARS = set("0123456789ABCDEFabcdef")
BASE32_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=")
BASE32HEX_CHARS = set("0123456789ABCDEFGHIJKLMNOPQRSTUV=")
CROCKFORD_CHARS = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
BASE58_CHARS = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
BASE64_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
BASE64URL_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")
BASE85_CHARS = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!#$%&()*+-;<=>?@^_`{|}~")
BASE36_CHARS = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
BASE62_CHARS = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
MORSE_CHARS = set(".-/ \n")
ALPHA_ONLY = set(string.ascii_letters)
ALPHA_UPPER = set(string.ascii_uppercase)


def _entropy(data: bytes) -> float:
    """Calculate Shannon entropy of byte data."""
    if not data:
        return 0.0
    freqs = [0] * 256
    for b in data:
        freqs[b] += 1
    ent = 0.0
    n = len(data)
    for c in freqs:
        if c:
            p = c / n
            ent -= p * math.log2(p)
    return ent


def _printable_ratio(data: bytes) -> float:
    """Calculate ratio of printable ASCII characters."""
    if not data:
        return 0.0
    printable = set(bytes(string.printable, 'ascii'))
    return sum(1 for b in data if b in printable) / len(data)


def _charset_match(text: str, charset: set) -> float:
    """Calculate ratio of characters in text that match a given charset."""
    if not text:
        return 0.0
    return sum(1 for c in text if c in charset) / len(text)


def _index_of_coincidence(text: str) -> float:
    """Calculate Index of Coincidence (IC) for text."""
    text = ''.join(c.upper() for c in text if c.isalpha())
    if len(text) < 2:
        return 0.0
    n = len(text)
    freqs = Counter(text)
    ic = sum(f * (f - 1) for f in freqs.values()) / (n * (n - 1))
    return ic


def _chi_squared(text: str) -> float:
    """Calculate chi-squared statistic against English frequency."""
    english_freq = {
        'E': 0.127, 'T': 0.091, 'A': 0.082, 'O': 0.075, 'I': 0.070,
        'N': 0.067, 'S': 0.063, 'H': 0.061, 'R': 0.060, 'D': 0.043,
        'L': 0.040, 'C': 0.028, 'U': 0.028, 'M': 0.024, 'W': 0.024,
        'F': 0.022, 'G': 0.020, 'Y': 0.020, 'P': 0.019, 'B': 0.015,
        'V': 0.010, 'K': 0.008, 'J': 0.002, 'X': 0.002, 'Q': 0.001, 'Z': 0.001
    }
    text = ''.join(c.upper() for c in text if c.isalpha())
    if not text:
        return float('inf')
    n = len(text)
    observed = Counter(text)
    chi2 = 0.0
    for letter in string.ascii_uppercase:
        expected = english_freq.get(letter, 0.001) * n
        obs = observed.get(letter, 0)
        chi2 += ((obs - expected) ** 2) / expected
    return chi2


def detect_encoders(text: str, data: bytes) -> List[Dict]:
    """Detect text-based encodings and representations."""
    candidates = []
    text_stripped = text.strip()
    
    # Hex detection
    hex_match = _charset_match(text_stripped.replace(" ", "").replace("\n", ""), BASE16_CHARS)
    if hex_match > 0.95 and len(text_stripped) % 2 == 0:
        candidates.append({"name": "hex", "score": 0.85 + 0.15 * hex_match, "category": "encoder"})
    
    # Base64 detection
    base64_match = _charset_match(text_stripped, BASE64_CHARS)
    if base64_match > 0.95:
        padding = text_stripped.count('=')
        if padding <= 2 and (len(text_stripped) % 4 == 0 or padding > 0):
            candidates.append({"name": "base64", "score": 0.80 + 0.20 * base64_match, "category": "encoder"})
    
    # Base64URL detection
    base64url_match = _charset_match(text_stripped, BASE64URL_CHARS)
    if base64url_match > 0.95 and '-' in text_stripped or '_' in text_stripped:
        candidates.append({"name": "base64url", "score": 0.78 + 0.22 * base64url_match, "category": "encoder"})
    
    # Base32 detection
    base32_match = _charset_match(text_stripped, BASE32_CHARS)
    if base32_match > 0.95:
        candidates.append({"name": "base32", "score": 0.75 + 0.25 * base32_match, "category": "encoder"})
    
    # Base32hex detection
    base32hex_match = _charset_match(text_stripped, BASE32HEX_CHARS)
    if base32hex_match > 0.95 and any(c in text_stripped for c in "0123456789"):
        candidates.append({"name": "base32hex", "score": 0.73 + 0.27 * base32hex_match, "category": "encoder"})
    
    # Crockford Base32
    crockford_match = _charset_match(text_stripped, CROCKFORD_CHARS)
    if crockford_match > 0.95 and not any(c in text_stripped for c in "ILO"):
        candidates.append({"name": "crockford_base32", "score": 0.72 + 0.28 * crockford_match, "category": "encoder"})
    
    # Base58 detection
    base58_match = _charset_match(text_stripped, BASE58_CHARS)
    if base58_match > 0.95 and not any(c in text_stripped for c in "0OIl"):
        candidates.append({"name": "base58", "score": 0.70 + 0.30 * base58_match, "category": "encoder"})
    
    # Base36 detection
    base36_match = _charset_match(text_stripped.upper(), BASE36_CHARS)
    if base36_match > 0.98 and text_stripped.isupper():
        candidates.append({"name": "base36", "score": 0.68 + 0.32 * base36_match, "category": "encoder"})
    
    # Base62 detection
    base62_match = _charset_match(text_stripped, BASE62_CHARS)
    if base62_match > 0.98:
        candidates.append({"name": "base62", "score": 0.67 + 0.33 * base62_match, "category": "encoder"})
    
    # JWT detection
    if text_stripped.count('.') == 2:
        parts = text_stripped.split('.')
        if all(len(p) > 0 for p in parts):
            jwt_score = min(_charset_match(p, BASE64URL_CHARS) for p in parts)
            if jwt_score > 0.95:
                candidates.append({"name": "jwt", "score": 0.90 + 0.10 * jwt_score, "category": "encoder"})
    
    # PEM armor detection
    if "-----BEGIN" in text and "-----END" in text:
        candidates.append({"name": "pem_armor", "score": 0.95, "category": "armor"})
    
    # PGP ASCII armor detection
    if "-----BEGIN PGP" in text and "-----END PGP" in text:
        candidates.append({"name": "pgp_armor", "score": 0.96, "category": "armor"})
    
    # URL encoding detection
    percent_count = text.count('%')
    if percent_count > 0:
        url_score = min(0.9, percent_count / len(text) * 10)
        if url_score > 0.3:
            candidates.append({"name": "url_encoded", "score": 0.60 + 0.40 * url_score, "category": "encoder"})
    
    # HTML entities detection
    if '&' in text and ';' in text:
        entity_pattern = r'&[a-zA-Z0-9#]+;'
        entities = len(re.findall(entity_pattern, text))
        if entities > 0:
            entity_score = min(0.9, entities / (len(text) / 10))
            candidates.append({"name": "html_entities", "score": 0.65 + 0.35 * entity_score, "category": "encoder"})
    
    # UUencode detection
    if text.startswith("begin ") and "\nend\n" in text:
        candidates.append({"name": "uuencode", "score": 0.88, "category": "encoder"})
    
    # Quoted-Printable detection
    if '=' in text:
        qp_pattern = r'=[0-9A-Fa-f]{2}'
        qp_matches = len(re.findall(qp_pattern, text))
        if qp_matches > 0:
            qp_score = min(0.9, qp_matches / (len(text) / 10))
            candidates.append({"name": "quoted_printable", "score": 0.62 + 0.38 * qp_score, "category": "encoder"})
    
    # Bech32/Bech32m detection (cryptocurrency addresses)
    bech32_pattern = r'^[a-z]{2,}1[ac-hj-np-z02-9]{38,}$'
    if re.match(bech32_pattern, text_stripped.lower()):
        candidates.append({"name": "bech32", "score": 0.85, "category": "encoder"})
    
    # Punycode detection
    if text_stripped.startswith("xn--"):
        candidates.append({"name": "punycode", "score": 0.87, "category": "encoder"})
    
    # Morse code detection
    morse_match = _charset_match(text_stripped, MORSE_CHARS)
    if morse_match > 0.95 and ('.' in text or '-' in text):
        candidates.append({"name": "morse_code", "score": 0.70 + 0.30 * morse_match, "category": "classical_cipher"})
    
    return candidates


def detect_classical_substitution(text: str) -> List[Dict]:
    """Detect classical substitution and polyalphabetic ciphers."""
    candidates = []
    alpha_only = ''.join(c for c in text if c.isalpha())
    
    if len(alpha_only) < 20:
        return candidates
    
    ic = _index_of_coincidence(alpha_only)
    chi2 = _chi_squared(alpha_only)
    
    # Normal English IC ≈ 0.065-0.068
    # Random/polyalphabetic IC ≈ 0.038-0.045
    # Monoalphabetic substitution IC ≈ 0.065-0.068 (same as English)
    
    # Caesar/ROT13/Atbash (monoalphabetic)
    if 0.060 < ic < 0.075:
        # High IC suggests monoalphabetic
        if chi2 < 100:  # Reasonably close to English
            candidates.append({"name": "plaintext_or_simple_substitution", "score": 0.55, "category": "classical_cipher", "params": {"ic": round(ic, 4), "chi2": round(chi2, 2)}})
        else:
            # High IC but high chi2 suggests monoalphabetic substitution
            candidates.append({"name": "monoalphabetic_substitution", "score": 0.65, "category": "classical_cipher", "params": {"ic": round(ic, 4), "chi2": round(chi2, 2)}})
            candidates.append({"name": "caesar_rot13_atbash", "score": 0.60, "category": "classical_cipher", "params": {"ic": round(ic, 4)}})
    
    # Vigenère and polyalphabetic ciphers
    if 0.038 < ic < 0.055:
        # Low IC suggests polyalphabetic
        candidates.append({"name": "vigenere_polyalphabetic", "score": 0.70, "category": "classical_cipher", "params": {"ic": round(ic, 4)}})
        candidates.append({"name": "autokey_vigenere", "score": 0.55, "category": "classical_cipher", "params": {"ic": round(ic, 4)}})
        candidates.append({"name": "beaufort_variant", "score": 0.52, "category": "classical_cipher", "params": {"ic": round(ic, 4)}})
        candidates.append({"name": "porta", "score": 0.50, "category": "classical_cipher", "params": {"ic": round(ic, 4)}})
        candidates.append({"name": "gronsfeld", "score": 0.48, "category": "classical_cipher", "params": {"ic": round(ic, 4)}})
    
    # Playfair detection (pairs of letters, no Q typically)
    if 'Q' not in alpha_only.upper() and len(alpha_only) % 2 == 0:
        candidates.append({"name": "playfair", "score": 0.45, "category": "classical_cipher", "params": {"ic": round(ic, 4)}})
    
    # Baconian cipher detection (only A and B, or binary-like)
    unique_chars = set(alpha_only.upper())
    if unique_chars <= {'A', 'B'} and len(unique_chars) == 2:
        candidates.append({"name": "baconian", "score": 0.85, "category": "classical_cipher"})
    
    # Polybius square (numeric pairs)
    if text.replace(" ", "").replace("\n", "").isdigit():
        candidates.append({"name": "polybius", "score": 0.60, "category": "classical_cipher"})
    
    return candidates


def detect_classical_fractionation(text: str) -> List[Dict]:
    """Detect classical fractionation and mixed ciphers."""
    candidates = []
    alpha_only = ''.join(c for c in text if c.isalpha())
    
    if len(alpha_only) < 20:
        return candidates
    
    ic = _index_of_coincidence(alpha_only)
    
    # Bifid, Trifid (intermediate IC)
    if 0.045 < ic < 0.062:
        candidates.append({"name": "bifid", "score": 0.50, "category": "classical_cipher", "params": {"ic": round(ic, 4)}})
        candidates.append({"name": "trifid", "score": 0.48, "category": "classical_cipher", "params": {"ic": round(ic, 4)}})
    
    # ADFGX (only A, D, F, G, X)
    upper = alpha_only.upper()
    unique_chars = set(upper)
    if unique_chars <= {'A', 'D', 'F', 'G', 'X'}:
        candidates.append({"name": "adfgx", "score": 0.80, "category": "classical_cipher"})
    
    # ADFGVX (only A, D, F, G, V, X)
    if unique_chars <= {'A', 'D', 'F', 'G', 'V', 'X'}:
        candidates.append({"name": "adfgvx", "score": 0.82, "category": "classical_cipher"})
    
    # Fractionated Morse (groups of dots, dashes, X)
    if all(c in '.-X \n' for c in text):
        candidates.append({"name": "fractionated_morse", "score": 0.75, "category": "classical_cipher"})
    
    # Nihilist cipher (numeric)
    if text.replace(" ", "").replace("\n", "").isdigit():
        candidates.append({"name": "nihilist", "score": 0.58, "category": "classical_cipher"})
    
    return candidates


def detect_classical_transposition(text: str) -> List[Dict]:
    """Detect classical transposition ciphers."""
    candidates = []
    alpha_only = ''.join(c for c in text if c.isalpha())
    
    if len(alpha_only) < 20:
        return candidates
    
    ic = _index_of_coincidence(alpha_only)
    chi2 = _chi_squared(alpha_only)
    
    # Transposition preserves IC (same letters, different order)
    # IC should be close to English (0.065-0.068)
    if 0.060 < ic < 0.075:
        # Check if letter frequencies are close to English
        if chi2 < 50:  # Very close to English frequencies
            candidates.append({"name": "transposition_cipher", "score": 0.62, "category": "classical_cipher", "params": {"ic": round(ic, 4), "chi2": round(chi2, 2)}})
            candidates.append({"name": "columnar_transposition", "score": 0.58, "category": "classical_cipher", "params": {"ic": round(ic, 4)}})
            candidates.append({"name": "rail_fence", "score": 0.55, "category": "classical_cipher", "params": {"ic": round(ic, 4)}})
            candidates.append({"name": "route_cipher", "score": 0.52, "category": "classical_cipher", "params": {"ic": round(ic, 4)}})
            candidates.append({"name": "scytale", "score": 0.50, "category": "classical_cipher", "params": {"ic": round(ic, 4)}})
    
    return candidates


def detect_containers(data: bytes) -> List[Dict]:
    """Detect common file containers and formats."""
    candidates = []
    
    # Magic number detection
    if data.startswith(b'%PDF'):
        candidates.append({"name": "pdf", "score": 0.98, "category": "container"})
    
    if data.startswith(b'PK\x03\x04') or data.startswith(b'PK\x05\x06'):
        candidates.append({"name": "zip", "score": 0.96, "category": "container"})
    
    if data.startswith(b'\x1f\x8b\x08'):
        candidates.append({"name": "gzip", "score": 0.97, "category": "container"})
    
    if data.startswith(b'BZh'):
        candidates.append({"name": "bzip2", "score": 0.95, "category": "container"})
    
    if data.startswith(b'\xfd7zXZ\x00'):
        candidates.append({"name": "xz_lzma", "score": 0.95, "category": "container"})
    
    if data.startswith(b'7z\xbc\xaf\x27\x1c'):
        candidates.append({"name": "7z", "score": 0.96, "category": "container"})
    
    if data.startswith(b'\x28\xb5\x2f\xfd'):
        candidates.append({"name": "zstd", "score": 0.94, "category": "container"})
    
    if data.startswith(b'\x04\x22\x4d\x18'):
        candidates.append({"name": "lz4", "score": 0.93, "category": "container"})
    
    # OpenSSH key detection
    if b'-----BEGIN OPENSSH PRIVATE KEY-----' in data:
        candidates.append({"name": "openssh_key", "score": 0.97, "category": "container"})
    
    # PKCS formats
    if b'-----BEGIN PRIVATE KEY-----' in data:
        candidates.append({"name": "pkcs8", "score": 0.96, "category": "container"})
    
    if b'-----BEGIN RSA PRIVATE KEY-----' in data:
        candidates.append({"name": "pkcs1", "score": 0.96, "category": "container"})
    
    # X.509 certificate
    if b'-----BEGIN CERTIFICATE-----' in data:
        candidates.append({"name": "x509_cert", "score": 0.97, "category": "container"})
    
    return candidates


def detect_high_entropy_ciphertext(data: bytes, ent: float, pr: float) -> List[Dict]:
    """Detect high-entropy modern ciphertext."""
    candidates = []
    
    # High entropy, low printable ratio suggests binary ciphertext
    if ent > 7.5 and pr < 0.3:
        candidates.append({
            "name": "high_entropy_ciphertext",
            "score": 0.75,
            "category": "modern_cipher",
            "params": {
                "entropy": round(ent, 3),
                "printable_ratio": round(pr, 3),
                "likely_ciphers": [
                    "AES", "3DES", "Blowfish", "Twofish", "ChaCha20", 
                    "Salsa20", "RC4", "Serpent", "Camellia"
                ]
            }
        })
    
    # Medium-high entropy with high printable ratio (encoded ciphertext)
    elif ent > 6.5 and pr > 0.9:
        candidates.append({
            "name": "encoded_ciphertext",
            "score": 0.65,
            "category": "modern_cipher",
            "params": {
                "entropy": round(ent, 3),
                "printable_ratio": round(pr, 3),
                "note": "possibly base64/hex encoded ciphertext"
            }
        })
    
    return candidates


def detect(inline_input: str) -> dict:
    """
    Main detection function for inline text input.
    
    Args:
        inline_input: String containing the text to analyze
        
    Returns:
        Dictionary with metrics and ranked candidates
    """
    # Convert input to bytes for entropy calculation
    data = inline_input.encode('utf-8', errors='ignore')
    
    # Calculate metrics
    ent = _entropy(data)
    pr = _printable_ratio(data)
    ic = _index_of_coincidence(inline_input)
    
    # Run all detectors
    candidates = []
    
    # Detect encoders and armor
    candidates.extend(detect_encoders(inline_input, data))
    
    # Detect classical ciphers
    candidates.extend(detect_classical_substitution(inline_input))
    candidates.extend(detect_classical_fractionation(inline_input))
    candidates.extend(detect_classical_transposition(inline_input))
    
    # Detect containers
    candidates.extend(detect_containers(data))
    
    # Detect high-entropy ciphertext
    candidates.extend(detect_high_entropy_ciphertext(data, ent, pr))
    
    # Remove duplicates and sort by score
    seen = set()
    unique_candidates = []
    for c in candidates:
        key = (c["name"], c.get("category", ""))
        if key not in seen:
            seen.add(key)
            unique_candidates.append(c)
    
    unique_candidates.sort(key=lambda c: c["score"], reverse=True)
    
    # Build result
    result = {
        "input_length": len(inline_input),
        "metrics": {
            "entropy": round(ent, 4),
            "printable_ratio": round(pr, 4),
            "index_of_coincidence": round(ic, 4)
        },
        "candidates": unique_candidates[:15]  # Top 15 candidates
    }
    
    return result