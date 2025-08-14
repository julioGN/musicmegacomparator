"""
Setup script for MusicWeb - Professional Music Library Management Suite
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements
def read_requirements(filename):
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="musicweb",
    version="1.0.0",
    author="MusicWeb Team",
    author_email="contact@musicweb.app",
    description="Professional Music Library Management Suite",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/musicweb",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements("requirements.txt"),
    extras_require={
        "dev": read_requirements("requirements-dev.txt"),
        "test": ["pytest", "pytest-cov", "pytest-mock"],
        "docs": ["mkdocs", "mkdocs-material", "mkdocs-mermaid2-plugin"],
    },
    entry_points={
        "console_scripts": [
            "musicweb=musicweb.cli.main:cli",
            "musicweb-web=musicweb.web.app:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="music library management streaming spotify apple youtube comparison",
    project_urls={
        "Bug Reports": "https://github.com/your-username/musicweb/issues",
        "Source": "https://github.com/your-username/musicweb",
        "Documentation": "https://musicweb.readthedocs.io/",
    },
)