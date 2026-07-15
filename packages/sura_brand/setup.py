from setuptools import setup, find_packages

setup(
    name="sura-brand",
    version="0.1.0",
    packages=find_packages(),
    package_data={"sura_brand": ["assets/*.png", "assets/*.jpg", "assets/*.svg"]},
    install_requires=[
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
        "numpy>=1.24.0",
    ],
)
