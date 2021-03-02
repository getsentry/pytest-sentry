from setuptools import setup

setup(
    name="pytest-sentry",
    description="A pytest plugin to send testrun information to Sentry.io",
    long_description=open("README.rst").read(),
    author="Markus Unterwaditzer",
    version="0.1.7",
    license="MIT",
    author_email="markus@unterwaditzer.net",
    url="https://github.com/untitaker/pytest-sentry",
    py_modules=["pytest_sentry"],
    entry_points={"pytest11": ["sentry = pytest_sentry"]},
    install_requires=["pytest", "sentry-sdk", "wrapt"],
)
