"""Include prebuilt offline web assets for normal pip and wheel installation."""
from pathlib import Path
from shutil import copytree
from setuptools import setup
from setuptools.command.build_py import build_py

class BuildWithViewer(build_py):
    def run(self):
        super().run()
        root=Path(__file__).parent
        for source,target in [('viewer','web'),('schemas','schemas')]:
            copytree(root/source,Path(self.build_lib)/'easy_to_3d'/target,dirs_exist_ok=True)

setup(cmdclass={'build_py':BuildWithViewer})
