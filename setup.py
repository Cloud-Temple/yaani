import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="yaani-ady",
    version="1.0.0",
    author="Antoine DELANNOY",
    author_email="antoine.j.m.delannoy@gmail.com",
    description="An Ansible dynamic inventory plugin",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Cloud-Temple/yaani.git",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)