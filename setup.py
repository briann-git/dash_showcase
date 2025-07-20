from setuptools import setup, find_packages

setup(
    name="dash-mcp-showcase",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "dash>=3.1.1,<4.0.0",
        "dash-bootstrap-components>=2.0.3,<3.0.0",
        "python-dotenv>=1.1.1,<2.0.0",
        "openai>=1.97.0,<2.0.0",
        "gunicorn>=23.0.0,<24.0.0",
        "google-cloud-secret-manager>=2.20.0,<3.0.0",
        "requests>=2.31.0",
    ],
    python_requires=">=3.10",
)
