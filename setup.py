from setuptools import setup, find_packages

setup(
    name="shadowvendor",
    version="14.0.2",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "plotly>=5.18.0",
        "tqdm>=4.66.1",
        "rich>=13.7.0",
    ],
    python_requires=">=3.9",
    author="Stewart Alexander",
    author_email="stewart@stewalexander.com",
    description="Network device vendor analysis tool - Transform MAC address tables into interactive dashboards, detect new vendors, and export SIEM events for security monitoring",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/StewAlexander-com/ShadowVendor",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
