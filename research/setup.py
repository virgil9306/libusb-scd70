from setuptools import setup, Extension
import subprocess

# Get libusb paths from pkg-config
def get_pkg_config(package, option):
    try:
        result = subprocess.run(['pkg-config', option, package], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip().split()
    except:
        return []

libusb_cflags = get_pkg_config('libusb-1.0', '--cflags')
libusb_libs = get_pkg_config('libusb-1.0', '--libs')

# Parse flags
include_dirs = [flag[2:] for flag in libusb_cflags if flag.startswith('-I')]
library_dirs = [flag[2:] for flag in libusb_libs if flag.startswith('-L')]
libraries = [flag[2:] for flag in libusb_libs if flag.startswith('-l')]

# Fallback to common paths if pkg-config fails
if not include_dirs:
    include_dirs = ['/opt/homebrew/include', '/usr/local/include']
if not library_dirs:
    library_dirs = ['/opt/homebrew/lib', '/usr/local/lib']
if not libraries:
    libraries = ['usb-1.0']

usb_reader_module = Extension(
    'usb_reader',
    sources=['usb_reader.c'],
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_compile_args=['-O3']  # Optimize for speed
)

setup(
    name='usb_reader',
    version='1.0',
    description='Fast USB reading module',
    ext_modules=[usb_reader_module],
)
