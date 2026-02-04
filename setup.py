from setuptools import setup, find_packages

setup(
    name="alphax_master_pos",
    version="0.1.0",
    description="Sector-agnostic Master POS platform for ERPNext / Frappe",
    author="AlphaX",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
