from setuptools import setup, find_packages

setup(
    name="backend",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask',
        'Flask-SQLAlchemy',
        'Flask-Login',
        'Flask-CORS',
        'python-dotenv',
        'openai',
    ],
)
