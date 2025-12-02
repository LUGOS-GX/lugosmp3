# setup.py
from setuptools import setup, find_packages

setup(
    name="youtube-downloader",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "Flask==2.3.3",
        "yt-dlp==2023.11.16",
    ],
)