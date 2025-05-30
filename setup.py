from setuptools import setup, find_packages

try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "A tool for extracting structured information from documents using AI"

setup(
    name='metaminer',
    version='0.3.1',
    packages=find_packages(),
    install_requires=[
        'openai>=1.0.0',
        'pandas>=1.3.0',
        'pydantic>=2.0.0',
        'pypandoc>=1.5',
        'PyMuPDF>=1.20.0',
    ],
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-mock',
        ],
    },
    entry_points={
        'console_scripts': [
            'metaminer=metaminer.cli:main',
        ],
    },
    author='Travis Adams',
    author_email='tadams792@gmail.com',
    description='Extract structured information from documents using AI',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/travis4dams/metaminer",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
)
