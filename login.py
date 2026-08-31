import json
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path


URL = "https://mvz2expand.wiki.gg/zh/api.php"
ACCOUNT_PATH = Path(__file__).with_name("account.txt")


def load_accounts():
    lines = [line.strip() for line in ACCOUNT_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) < 2 or len(lines) % 2:
        raise RuntimeError("account.txt 格式错误：每个账号需要两行，第一行为用户名，第二行为密码")
    return list(zip(lines[0::2], lines[1::2]))


class MwApi:
    def __init__(self, url=URL):
        self.url = url
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        self.current_account = None
        self.csrf_token = None

    def request(self, values):
        payload = {"format": "json", "formatversion": "2", **values}
        request = urllib.request.Request(
            self.url,
            data=urllib.parse.urlencode(payload).encode("utf-8"),
            headers={"User-Agent": "MVZ2-Json-Uploader/1.0"},
        )
        with self.opener.open(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8-sig"))
        if "error" in result:
            raise RuntimeError(result["error"].get("info", str(result["error"])))
        return result

    def login(self, num=1):
        accounts = load_accounts()
        if not 1 <= num <= len(accounts):
            raise RuntimeError("账号序号超出范围")
        username, password = accounts[num - 1]
        token = self.request({
            "action": "query",
            "meta": "tokens",
            "type": "login",
        })["query"]["tokens"]["logintoken"]
        login = self.request({
            "action": "login",
            "lgname": username,
            "lgpassword": password,
            "lgtoken": token,
        })["login"]
        if login.get("result") != "Success":
            raise RuntimeError("登录失败：" + login.get("reason", login.get("result", "未知错误")))
        self.current_account = num
        self.csrf_token = None

    def get_token(self):
        if self.current_account is None:
            self.login()
        token = self.request({
            "action": "query",
            "meta": "tokens",
            "type": "csrf",
        })["query"]["tokens"]["csrftoken"]
        if token == "+\\":
            self.login(self.current_account)
            return self.get_token()
        self.csrf_token = token
        return token

    def post_with_token(self, values):
        if self.csrf_token is None:
            self.get_token()
        data = {**values, "token": self.csrf_token}
        result = self.request(data)
        if result.get("error", {}).get("code") == "badtoken":
            data["token"] = self.get_token()
            result = self.request(data)
        return result

    def upload_text(self, title, text, summary):
        edit = self.post_with_token({
            "action": "edit",
            "title": title,
            "text": text,
            "summary": summary,
            "assert": "user",
            "watchlist": "nochange",
        }).get("edit", {})
        if edit.get("result") != "Success":
            raise RuntimeError(str(edit))


api = MwApi()


def upload_text(title, text, summary):
    api.upload_text(title, text, summary)