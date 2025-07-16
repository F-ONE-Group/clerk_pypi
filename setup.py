from typing import List
from setuptools import setup, find_packages


def get_requirements(root_path: str) -> List[str]:
    with open(f"{root_path}/requirements.txt") as f:
        return f.read().splitlines()


core_requirements = get_requirements(".")
gui_requirements = get_requirements("./clerk/gui_automation")


setup(
    name="clerk-sdk",
    version="0.2.7",
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
    install_requires=core_requirements,
    extras_require={
        "all": core_requirements + gui_requirements,
        "gui-automation": gui_requirements,
    },
)
