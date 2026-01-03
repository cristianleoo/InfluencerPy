import json
import os

import requests


class SubstackAuth:
    """Handles authentication for Substack API requests."""

    def __init__(
        self,
        cookies_path: str = None,
        cookies_dict: dict = None,
    ):
        """
        Initialize authentication handler.

        Parameters
        ----------
        cookies_path : str, optional
            Path to retrieve session cookies from (legacy support)
        cookies_dict : dict, optional
            Dictionary with cookie values: {'sid': '...', 'lli': '...'}
        """
        self.cookies_path = cookies_path
        self.session = requests.Session()
        self.authenticated = False

        # Set default headers
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        # Try to load cookies from dict first, then from file
        if cookies_dict:
            self.load_cookies_from_dict(cookies_dict)
            self.authenticated = True
        elif cookies_path and os.path.exists(cookies_path):
            self.load_cookies()
            self.authenticated = True
        else:
            if cookies_path:
                print(f"Cookies file not found at {self.cookies_path}. Please log in.")
            self.authenticated = False
            self.session.cookies.clear()

    def load_cookies_from_dict(self, cookies_dict: dict) -> bool:
        """
        Load cookies from a dictionary.

        Parameters
        ----------
        cookies_dict : dict
            Dictionary with 'sid' and 'lli' keys

        Returns
        -------
        bool
            True if cookies loaded successfully
        """
        try:
            # Set the essential Substack cookies
            if 'sid' in cookies_dict:
                self.session.cookies.set(
                    "substack.sid",
                    cookies_dict['sid'],
                    domain=".substack.com",
                    path="/",
                    secure=True,
                )
            
            if 'lli' in cookies_dict:
                self.session.cookies.set(
                    "substack.lli",
                    cookies_dict['lli'],
                    domain=".substack.com",
                    path="/",
                    secure=True,
                )

            return True

        except Exception as e:
            print(f"Failed to load cookies: {str(e)}")
            return False

    def load_cookies(self) -> bool:
        """
        Load cookies from file (legacy support).

        Returns
        -------
        bool
            True if cookies loaded successfully
        """
        try:
            with open(self.cookies_path, "r") as f:
                cookies = json.load(f)

            for cookie in cookies:
                self.session.cookies.set(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie.get("domain"),
                    path=cookie.get("path", "/"),
                    secure=cookie.get("secure", False),
                )

            return True

        except Exception as e:
            print(f"Failed to load cookies: {str(e)}")
            return False

    def get(self, url: str, **kwargs) -> requests.Response:
        """
        Make authenticated GET request.

        Parameters
        ----------
        url : str
            URL to request
        **kwargs
            Additional arguments to pass to requests.get

        Returns
        -------
        requests.Response
            Response object
        """
        return self.session.get(url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """
        Make authenticated POST request.

        Parameters
        ----------
        url : str
            URL to request
        **kwargs
            Additional arguments to pass to requests.post

        Returns
        -------
        requests.Response
            Response object
        """
        return self.session.post(url, **kwargs)