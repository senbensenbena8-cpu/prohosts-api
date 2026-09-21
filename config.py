# ProHosts Panel - Kendi Auth Sistemimiz
API_KEY = "PH_" + __import__("hashlib").sha256(b"prohosts.org_v1_2026").hexdigest()[:32]
SECRET = "PH_SEC_" + __import__("hashlib").sha256(b"prohosts.org_secret_2026").hexdigest()[:40]
LOGIN_EMAIL = "senbensenbena8@gmail.com"
LOGIN_PASSWORD = "qazxcvbnm12A"
HASH = "aa217a6339"
