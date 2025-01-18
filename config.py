import os
from typing import Optional

class Config:
    def __init__(self):
        self.github_token: Optional[str] = os.getenv('GITHUB_TOKEN')
        self.github_username: Optional[str] = os.getenv('GITHUB_USERNAME')

    @property
    def is_valid(self) -> bool:
        return bool(self.github_token and self.github_username)
