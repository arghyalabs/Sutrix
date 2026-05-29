from setuptools import setup, find_packages

setup(
    name="scientific-data-orchestrator",
    version="1.0.0",
    description="Automated curation, validation, and hierarchical segregation of scientific datasets",
    author="Research Team",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "numpy>=1.24.0",
        "streamlit>=1.28.0",
        "chardet>=5.2.0",
        "requests>=2.31.0",
        "jsonschema>=4.19.0",
        "reportlab>=4.0.0",
        "xlsxwriter>=3.1.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ]
    },
)
