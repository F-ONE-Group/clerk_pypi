from setuptools import setup, find_packages

requirements = []
with open("./requirements.txt", "r") as f:
    requirements = f.readlines()

setup(
    name="clerk-sdk",
    version="0.1.2",
    description="Library for interacting with Clerk",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="F-ONE Group",
    author_email="admin@f-one.group",
    url="https://github.com/F-ONE-Group/clerk_pypi",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
)
