from setuptools import setup, find_packages

setup(
    name="ai_sql_converter",
    version="1.1.2",
    packages=find_packages(),
    install_requires=[
        "openai>=1.3.0",
        "anthropic>=0.5.0",
        "python-dotenv>=1.0.0",
        'colorama>=0.4.6; platform_system=="Windows"',
    ],
    extras_require={
        "test": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
        ],
    },
    python_requires=">=3.8",
    author="kamusis",
    description="AI-powered SQL script converter between different database systems",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/kamusis/ai_sql_converter",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
