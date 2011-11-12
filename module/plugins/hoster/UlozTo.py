# -*- coding: utf-8 -*-
"""
    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 3 of the License,
    or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, see <http://www.gnu.org/licenses/>.

    @author: zoidberg
"""

import re
from module.plugins.internal.SimpleHoster import SimpleHoster, parseFileInfo
from module.network.RequestFactory import getURL

def getInfo(urls):
    result = []

    for url in urls:
        try:
            file_info = parseFileInfo(IfileIt, url, getURL(url, decode=True)) 
            result.append(file_info)
        except Exception, e:
            self.logError(e)
            result.append((url, 0, 1, url))

    yield result

class UlozTo(SimpleHoster):
    __name__ = "UlozTo"
    __type__ = "hoster"
    __pattern__ = r"http://(\w*\.)?(uloz\.to|ulozto\.(cz|sk|net)|bagruj.cz|zachowajto.pl)/.*"
    __version__ = "0.71"
    __description__ = """uloz.to"""
    __config__ = [("reuseCaptcha", "bool", "Reuse captcha", "True"),
        ("captchaUser", "str", "captcha_user", ""),
        ("captchaNb", "str", "captcha_nb", "")]
    __author_name__ = ("zoidberg")

    FILE_URL_PATTERN = r'<form name="dwn" action="([^"]+)"'
    FILE_NAME_PATTERN = r'<h2 class="nadpis" style="margin-left:196px;"><a href="[^"]+">([^<]+)</a></h2>'
    CAPTCHA_PATTERN = r'<img style=".*src="([^"]+)" alt="Captcha" class="captcha"'
    CAPTCHA_NB_PATTERN = r'<input class="captcha_nb" type="hidden" name="captcha_nb" value="([0-9]+)" >'
    FILE_OFFLINE_PATTERN = r'href="http://www.ulozto.net/(neexistujici|smazano)/\?lg=en&amp;'
    PASSWD_PATTERN = r'<input type="password" class="text" name="file_password" id="frmfilepasswordForm-file_password" />'
    LIVE_URL_PATTERN = r'<div id="flashplayer"[^>]*>\s*<a href="([^"]+)"'
    LIVE_NAME_PATTERN = r'<a share_url="[^&]*&amp;t=([^"]+)"'
    FILE_SIZE_PATTERN = r'<div class="info_velikost" style="top:-55px;">\s*<div>[^<]*\s+([0-9.]+)\s([kKMG]i?B)\s*</div>\s*</div>'
    VIPLINK_PATTERN = r'<a href="[^"]*\?disclaimer=1" class="linkVip">'

    def setup(self):
        self.multiDL = False

    def process(self, pyfile):
        self.html = self.load(pyfile.url, decode=True)
        self.getFileInfo()

        if re.search(self.VIPLINK_PATTERN, self.html):
            self.html = self.load(pyfile.url, get={"disclaimer": "1"})

        found = re.search(self.LIVE_URL_PATTERN, self.html)
        if found is not None:
            # Uloz.to LIVE       
            parsed_url = found.group(1)
            self.logDebug("LIVE URL:" + parsed_url)

            found = re.search(self.LIVE_NAME_PATTERN, self.html)
            if found is None:
                self.fail("Parse error (LIVE_NAME)")
            pyfile.name = found.group(1)
            self.log.debug("LIVE NAME:" + pyfile.name)

            self.download(parsed_url)
        else:
            # Uloz.to DATA
            # parse the name from the site and set attribute in pyfile
            found = re.search(self.FILE_NAME_PATTERN, self.html)
            if found is None:
                self.fail("Parse error (FILENAME)")
            pyfile.name = found.group(1)
            self.log.debug("PARSED_NAME:" + pyfile.name)

            found = re.search(self.FILE_URL_PATTERN, self.html)
            if found is None:
                self.fail("Parse error (URL)")
            parsed_url = found.group(1)
            self.log.debug("PARSED_URL:" + parsed_url)

            # get and decrypt captcha
            reuse_captcha = self.getConfig("reuseCaptcha")
            captcha = self.getConfig("captchaUser")
            captcha_nb = self.getConfig("captchaNb")
            captcha_url = "DUMMY"

            if not reuse_captcha or not captcha or not captcha_nb:
                found = re.search(self.CAPTCHA_PATTERN, self.html)
                if found is None:
                    self.fail("Parse error (CAPTCHA)")
                captcha_url = found.group(1)
                captcha = self.decryptCaptcha(captcha_url)
                found = re.search(self.CAPTCHA_NB_PATTERN, self.html)
                if found is None:
                    self.fail("Parse error (CAPTCHA_NB)")
                captcha_nb = found.group(1)
            self.log.debug('CAPTCHA_URL:' + captcha_url + ' CAPTCHA:' + captcha + ' CAPTCHA_NB:' + captcha_nb)

            # download the file, destination is determined by pyLoad
            self.download(parsed_url, post={
                "captcha_user": captcha,
                "captcha_nb": captcha_nb
            })

            check = self.checkDownload({
                "wrong_captcha": re.compile(self.CAPTCHA_PATTERN),
                "offline": re.compile(self.FILE_OFFLINE_PATTERN),
                "passwd": self.PASSWD_PATTERN
            })

            if check == "wrong_captcha":
                if reuse_captcha:
                    self.setConfig("captchaUser", "")
                    self.setConfig("captchaNb", "")
                self.invalidCaptcha()
                self.retry(reason="Wrong captcha code")
            elif check == "offline":
                self.offline()
            elif check == "passwd":
                self.fail("Password protected")

            if reuse_captcha:
                self.setConfig("captchaUser", captcha)
                self.setConfig("captchaNb", captcha_nb)
        