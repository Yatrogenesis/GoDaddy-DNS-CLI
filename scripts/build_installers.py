#!/usr/bin/env python3
"""
Build installers for GoDaddy DNS CLI across multiple platforms
"""

import os
import sys
import shutil
import subprocess
import platform
import tempfile
from pathlib import Path
from typing import Dict, List

# Build configuration
BUILD_CONFIG = {
    'app_name': 'GoDaddy DNS CLI',
    'executable_name': 'godaddy-cli',
    'version': '2.0.0',
    'author': 'Yatrogenesis',
    'description': 'Enterprise-grade CLI tool for GoDaddy DNS management',
    'url': 'https://github.com/Yatrogenesis/GoDaddy-DNS-CLI',
    'license': 'MIT',
}

class InstallerBuilder:
    """Build installers for different platforms"""

    def __init__(self, build_dir: Path):
        self.build_dir = build_dir
        self.dist_dir = build_dir / 'dist'
        self.installers_dir = build_dir / 'installers'
        self.current_platform = platform.system().lower()

        # Ensure directories exist
        self.dist_dir.mkdir(exist_ok=True)
        self.installers_dir.mkdir(exist_ok=True)

    def clean_build(self):
        """Clean previous builds"""
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        if self.installers_dir.exists():
            shutil.rmtree(self.installers_dir)

        self.dist_dir.mkdir(exist_ok=True)
        self.installers_dir.mkdir(exist_ok=True)

    def build_web_ui(self):
        """Build web UI"""
        print("Building web UI...")
        web_ui_dir = self.build_dir / 'web-ui'

        if not web_ui_dir.exists():
            print("Warning: web-ui directory not found, skipping...")
            return

        # Install dependencies and build
        subprocess.run(['npm', 'ci'], cwd=web_ui_dir, check=True)
        subprocess.run(['npm', 'run', 'build'], cwd=web_ui_dir, check=True)
        print("Web UI built successfully")

    def create_pyinstaller_spec(self) -> Path:
        """Create PyInstaller spec file"""
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['godaddy_cli/cli.py'],
    pathex=['{self.build_dir}'],
    binaries=[],
    datas=[
        ('godaddy_cli/web/static', 'godaddy_cli/web/static'),
        ('godaddy_cli/templates', 'godaddy_cli/templates'),
        ('godaddy_cli/config', 'godaddy_cli/config'),
    ],
    hiddenimports=[
        'godaddy_cli.commands.dns',
        'godaddy_cli.commands.domain',
        'godaddy_cli.commands.config',
        'godaddy_cli.commands.auth',
        'godaddy_cli.commands.template',
        'godaddy_cli.commands.bulk',
        'godaddy_cli.commands.export',
        'godaddy_cli.commands.import_cmd',
        'godaddy_cli.commands.monitor',
        'godaddy_cli.commands.init',
        'godaddy_cli.commands.deploy',
        'uvicorn',
        'uvicorn.workers',
        'fastapi',
        'aiohttp',
        'rich',
        'click',
        'yaml',
        'toml',
        'jinja2',
        'cryptography',
        'keyring',
        'pkg_resources.py2_warn',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{BUILD_CONFIG["executable_name"]}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
)
'''

        spec_file = self.build_dir / f'{BUILD_CONFIG["executable_name"]}.spec'
        with open(spec_file, 'w') as f:
            f.write(spec_content)

        return spec_file

    def create_version_info(self):
        """Create version info for Windows builds"""
        if self.current_platform != 'windows':
            return

        version_info = f'''# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({BUILD_CONFIG["version"].replace(".", ", ")}, 0),
    prodvers=({BUILD_CONFIG["version"].replace(".", ", ")}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'{BUILD_CONFIG["author"]}'),
            StringStruct(u'FileDescription', u'{BUILD_CONFIG["description"]}'),
            StringStruct(u'FileVersion', u'{BUILD_CONFIG["version"]}'),
            StringStruct(u'InternalName', u'{BUILD_CONFIG["executable_name"]}'),
            StringStruct(u'LegalCopyright', u'© {BUILD_CONFIG["author"]}. All rights reserved.'),
            StringStruct(u'OriginalFilename', u'{BUILD_CONFIG["executable_name"]}.exe'),
            StringStruct(u'ProductName', u'{BUILD_CONFIG["app_name"]}'),
            StringStruct(u'ProductVersion', u'{BUILD_CONFIG["version"]}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''

        with open(self.build_dir / 'version_info.txt', 'w') as f:
            f.write(version_info)

    def build_executable(self):
        """Build standalone executable with PyInstaller"""
        print("Building standalone executable...")

        # Install PyInstaller if not available
        try:
            import PyInstaller
        except ImportError:
            print("Installing PyInstaller...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)

        # Create spec file and version info
        spec_file = self.create_pyinstaller_spec()
        self.create_version_info()

        # Build with PyInstaller
        cmd = [
            'pyinstaller',
            str(spec_file),
            '--clean',
            '--noconfirm',
            f'--distpath={self.dist_dir}',
            f'--workpath={self.build_dir}/build',
        ]

        subprocess.run(cmd, cwd=self.build_dir, check=True)
        print("Executable built successfully")

    def create_windows_installer(self):
        """Create Windows installer using Inno Setup"""
        if self.current_platform != 'windows':
            return

        print("Creating Windows installer...")

        # Create Inno Setup script
        iss_content = f'''[Setup]
AppName={BUILD_CONFIG["app_name"]}
AppVersion={BUILD_CONFIG["version"]}
AppPublisher={BUILD_CONFIG["author"]}
AppPublisherURL={BUILD_CONFIG["url"]}
AppSupportURL={BUILD_CONFIG["url"]}/issues
AppUpdatesURL={BUILD_CONFIG["url"]}/releases
DefaultDirName={{autopf}}\\{BUILD_CONFIG["app_name"]}
DefaultGroupName={BUILD_CONFIG["app_name"]}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir={self.installers_dir}
OutputBaseFilename={BUILD_CONFIG["executable_name"]}-{BUILD_CONFIG["version"]}-windows-x64-setup
SetupIconFile=assets\\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked
Name: "addtopath"; Description: "Add to PATH environment variable"; GroupDescription: "System integration"; Flags: unchecked

[Files]
Source: "{self.dist_dir}\\{BUILD_CONFIG["executable_name"]}.exe"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\{BUILD_CONFIG["app_name"]}"; Filename: "{{app}}\\{BUILD_CONFIG["executable_name"]}.exe"
Name: "{{group}}\\{{cm:UninstallProgram,{BUILD_CONFIG["app_name"]}}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{BUILD_CONFIG["app_name"]}"; Filename: "{{app}}\\{BUILD_CONFIG["executable_name"]}.exe"; Tasks: desktopicon

[Registry]
Root: HKLM; Subkey: "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{{olddata}};{{app}}"; Tasks: addtopath; Check: NeedsAddPath('{{app}}')

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

[Run]
Filename: "{{app}}\\{BUILD_CONFIG["executable_name"]}.exe"; Parameters: "--version"; Flags: postinstall skipifsilent runhidden
'''

        iss_file = self.build_dir / f'{BUILD_CONFIG["executable_name"]}.iss'
        with open(iss_file, 'w') as f:
            f.write(iss_content)

        # Try to find Inno Setup
        inno_paths = [
            'C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe',
            'C:\\Program Files\\Inno Setup 6\\ISCC.exe',
            'iscc.exe'  # If in PATH
        ]

        inno_setup = None
        for path in inno_paths:
            if Path(path).exists() or shutil.which(path):
                inno_setup = path
                break

        if not inno_setup:
            print("Warning: Inno Setup not found. Please install it to create Windows installer.")
            return

        # Build installer
        subprocess.run([inno_setup, str(iss_file)], check=True)
        print("Windows installer created successfully")

    def create_macos_installer(self):
        """Create macOS installer using pkgbuild"""
        if self.current_platform != 'darwin':
            return

        print("Creating macOS installer...")

        # Create app bundle structure
        app_name = f'{BUILD_CONFIG["app_name"]}.app'
        app_dir = self.dist_dir / app_name
        contents_dir = app_dir / 'Contents'
        macos_dir = contents_dir / 'MacOS'
        resources_dir = contents_dir / 'Resources'

        # Create directories
        macos_dir.mkdir(parents=True, exist_ok=True)
        resources_dir.mkdir(parents=True, exist_ok=True)

        # Copy executable
        shutil.copy2(
            self.dist_dir / BUILD_CONFIG["executable_name"],
            macos_dir / BUILD_CONFIG["executable_name"]
        )

        # Create Info.plist
        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>{BUILD_CONFIG["executable_name"]}</string>
    <key>CFBundleIdentifier</key>
    <string>com.yatrogenesis.godaddy-dns-cli</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{BUILD_CONFIG["app_name"]}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{BUILD_CONFIG["version"]}</string>
    <key>CFBundleVersion</key>
    <string>{BUILD_CONFIG["version"]}</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.developer-tools</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
'''

        with open(contents_dir / 'Info.plist', 'w') as f:
            f.write(plist_content)

        # Create DMG
        dmg_name = f'{BUILD_CONFIG["executable_name"]}-{BUILD_CONFIG["version"]}-macos-x64.dmg'
        dmg_path = self.installers_dir / dmg_name

        subprocess.run([
            'hdiutil', 'create',
            '-volname', BUILD_CONFIG["app_name"],
            '-srcfolder', str(app_dir),
            '-ov', '-format', 'UDZO',
            str(dmg_path)
        ], check=True)

        print("macOS installer created successfully")

    def create_linux_packages(self):
        """Create Linux packages (DEB, RPM, AppImage)"""
        if self.current_platform != 'linux':
            return

        print("Creating Linux packages...")

        # Create DEB package
        self.create_deb_package()

        # Create RPM package
        self.create_rpm_package()

        # Create AppImage
        self.create_appimage()

    def create_deb_package(self):
        """Create Debian package"""
        print("Creating DEB package...")

        # Create package structure
        pkg_name = f'{BUILD_CONFIG["executable_name"]}_{BUILD_CONFIG["version"]}_amd64'
        pkg_dir = self.dist_dir / pkg_name

        # Create directories
        (pkg_dir / 'DEBIAN').mkdir(parents=True, exist_ok=True)
        (pkg_dir / 'usr' / 'bin').mkdir(parents=True, exist_ok=True)
        (pkg_dir / 'usr' / 'share' / 'applications').mkdir(parents=True, exist_ok=True)
        (pkg_dir / 'usr' / 'share' / 'doc' / BUILD_CONFIG["executable_name"]).mkdir(parents=True, exist_ok=True)

        # Copy executable
        shutil.copy2(
            self.dist_dir / BUILD_CONFIG["executable_name"],
            pkg_dir / 'usr' / 'bin' / BUILD_CONFIG["executable_name"]
        )

        # Create control file
        control_content = f'''Package: {BUILD_CONFIG["executable_name"]}
Version: {BUILD_CONFIG["version"]}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: {BUILD_CONFIG["author"]} <support@godaddy-cli.dev>
Description: {BUILD_CONFIG["description"]}
 A powerful command-line interface for managing GoDaddy DNS records,
 inspired by Cloudflare's Wrangler. Streamline your DNS operations
 with enterprise-grade features.
Homepage: {BUILD_CONFIG["url"]}
'''

        with open(pkg_dir / 'DEBIAN' / 'control', 'w') as f:
            f.write(control_content)

        # Create desktop file
        desktop_content = f'''[Desktop Entry]
Version=1.0
Type=Application
Name={BUILD_CONFIG["app_name"]}
Comment={BUILD_CONFIG["description"]}
Exec={BUILD_CONFIG["executable_name"]}
Icon={BUILD_CONFIG["executable_name"]}
Terminal=true
Categories=Development;Network;
'''

        with open(pkg_dir / 'usr' / 'share' / 'applications' / f'{BUILD_CONFIG["executable_name"]}.desktop', 'w') as f:
            f.write(desktop_content)

        # Copy documentation
        if (self.build_dir / 'README.md').exists():
            shutil.copy2(self.build_dir / 'README.md', pkg_dir / 'usr' / 'share' / 'doc' / BUILD_CONFIG["executable_name"])

        # Build DEB package
        subprocess.run(['dpkg-deb', '--build', str(pkg_dir)], check=True)

        # Move to installers directory
        shutil.move(f'{pkg_dir}.deb', self.installers_dir)

        print("DEB package created successfully")

    def create_rpm_package(self):
        """Create RPM package"""
        print("Creating RPM package...")

        # Check if rpmbuild is available
        if not shutil.which('rpmbuild'):
            print("Warning: rpmbuild not found. Skipping RPM creation.")
            return

        # Create RPM build structure
        rpm_dir = self.dist_dir / 'rpm'
        for subdir in ['BUILD', 'RPMS', 'SOURCES', 'SPECS', 'SRPMS']:
            (rpm_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Create spec file
        spec_content = f'''Name: {BUILD_CONFIG["executable_name"]}
Version: {BUILD_CONFIG["version"]}
Release: 1%{{?dist}}
Summary: {BUILD_CONFIG["description"]}

License: {BUILD_CONFIG["license"]}
URL: {BUILD_CONFIG["url"]}
Source0: %{{name}}-%{{version}}.tar.gz

BuildArch: x86_64
Requires: python3

%description
{BUILD_CONFIG["description"]}

%prep
%setup -q

%build
# Nothing to build

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/usr/bin
cp {BUILD_CONFIG["executable_name"]} $RPM_BUILD_ROOT/usr/bin/

%files
%defattr(-,root,root,-)
/usr/bin/{BUILD_CONFIG["executable_name"]}

%changelog
* $(date "+%a %b %d %Y") {BUILD_CONFIG["author"]} <support@godaddy-cli.dev> - {BUILD_CONFIG["version"]}-1
- Initial package
'''

        spec_file = rpm_dir / 'SPECS' / f'{BUILD_CONFIG["executable_name"]}.spec'
        with open(spec_file, 'w') as f:
            f.write(spec_content)

        # Create source tarball
        source_dir = rpm_dir / f'{BUILD_CONFIG["executable_name"]}-{BUILD_CONFIG["version"]}'
        source_dir.mkdir(exist_ok=True)

        shutil.copy2(
            self.dist_dir / BUILD_CONFIG["executable_name"],
            source_dir / BUILD_CONFIG["executable_name"]
        )

        # Create tarball
        subprocess.run([
            'tar', 'czf',
            str(rpm_dir / 'SOURCES' / f'{BUILD_CONFIG["executable_name"]}-{BUILD_CONFIG["version"]}.tar.gz'),
            '-C', str(rpm_dir),
            f'{BUILD_CONFIG["executable_name"]}-{BUILD_CONFIG["version"]}'
        ], check=True)

        # Build RPM
        subprocess.run([
            'rpmbuild', '--define', f'_topdir {rpm_dir}',
            '-ba', str(spec_file)
        ], check=True)

        # Copy RPM to installers directory
        rpm_files = list((rpm_dir / 'RPMS' / 'x86_64').glob('*.rpm'))
        for rpm_file in rpm_files:
            shutil.copy2(rpm_file, self.installers_dir)

        print("RPM package created successfully")

    def create_appimage(self):
        """Create AppImage"""
        print("Creating AppImage...")

        # Check if appimagetool is available
        if not shutil.which('appimagetool'):
            print("Warning: appimagetool not found. Skipping AppImage creation.")
            return

        # Create AppDir structure
        appdir = self.dist_dir / f'{BUILD_CONFIG["app_name"]}.AppDir'
        (appdir / 'usr' / 'bin').mkdir(parents=True, exist_ok=True)

        # Copy executable
        shutil.copy2(
            self.dist_dir / BUILD_CONFIG["executable_name"],
            appdir / 'usr' / 'bin' / BUILD_CONFIG["executable_name"]
        )

        # Create desktop file
        desktop_content = f'''[Desktop Entry]
Version=1.0
Type=Application
Name={BUILD_CONFIG["app_name"]}
Comment={BUILD_CONFIG["description"]}
Exec={BUILD_CONFIG["executable_name"]}
Icon={BUILD_CONFIG["executable_name"]}
Terminal=true
Categories=Development;Network;
'''

        with open(appdir / f'{BUILD_CONFIG["executable_name"]}.desktop', 'w') as f:
            f.write(desktop_content)

        # Create AppRun script
        apprun_content = f'''#!/bin/bash
HERE="$(dirname "$(readlink -f "${{0}}")")"
export PATH="${{HERE}}/usr/bin:${{PATH}}"
exec "${{HERE}}/usr/bin/{BUILD_CONFIG["executable_name"]}" "$@"
'''

        apprun_path = appdir / 'AppRun'
        with open(apprun_path, 'w') as f:
            f.write(apprun_content)

        # Make AppRun executable
        apprun_path.chmod(0o755)

        # Build AppImage
        appimage_name = f'{BUILD_CONFIG["executable_name"]}-{BUILD_CONFIG["version"]}-linux-x64.AppImage'
        subprocess.run([
            'appimagetool',
            str(appdir),
            str(self.installers_dir / appimage_name)
        ], check=True)

        print("AppImage created successfully")

    def create_portable_archives(self):
        """Create portable ZIP/TAR.GZ archives"""
        print("Creating portable archives...")

        # Create portable directory
        portable_dir = self.dist_dir / f'{BUILD_CONFIG["executable_name"]}-{BUILD_CONFIG["version"]}-portable'
        portable_dir.mkdir(exist_ok=True)

        # Copy executable
        if self.current_platform == 'windows':
            exe_name = f'{BUILD_CONFIG["executable_name"]}.exe'
        else:
            exe_name = BUILD_CONFIG["executable_name"]

        shutil.copy2(self.dist_dir / exe_name, portable_dir / exe_name)

        # Copy documentation
        for doc_file in ['README.md', 'LICENSE', 'CHANGELOG.md']:
            doc_path = self.build_dir / doc_file
            if doc_path.exists():
                shutil.copy2(doc_path, portable_dir / doc_file)

        # Create archive
        if self.current_platform == 'windows':
            # Create ZIP for Windows
            archive_name = f'{BUILD_CONFIG["executable_name"]}-{BUILD_CONFIG["version"]}-{self.current_platform}-x64-portable.zip'
            shutil.make_archive(
                str(self.installers_dir / archive_name.replace('.zip', '')),
                'zip',
                str(portable_dir.parent),
                portable_dir.name
            )
        else:
            # Create TAR.GZ for Unix systems
            archive_name = f'{BUILD_CONFIG["executable_name"]}-{BUILD_CONFIG["version"]}-{self.current_platform}-x64-portable.tar.gz'
            shutil.make_archive(
                str(self.installers_dir / archive_name.replace('.tar.gz', '')),
                'gztar',
                str(portable_dir.parent),
                portable_dir.name
            )

        print(f"Portable archive created: {archive_name}")

    def build_all(self):
        """Build all installers for current platform"""
        print(f"Building installers for {self.current_platform}...")

        # Clean previous builds
        self.clean_build()

        # Build web UI
        self.build_web_ui()

        # Build executable
        self.build_executable()

        # Create platform-specific installers
        if self.current_platform == 'windows':
            self.create_windows_installer()
        elif self.current_platform == 'darwin':
            self.create_macos_installer()
        elif self.current_platform == 'linux':
            self.create_linux_packages()

        # Create portable archives for all platforms
        self.create_portable_archives()

        print("\nBuild completed successfully!")
        print(f"Installers created in: {self.installers_dir}")

        # List created files
        print("\nCreated files:")
        for file_path in self.installers_dir.glob('*'):
            print(f"  - {file_path.name}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Build GoDaddy DNS CLI installers')
    parser.add_argument('--clean', action='store_true', help='Clean build directories')
    parser.add_argument('--platform', choices=['windows', 'darwin', 'linux'],
                       help='Target platform (default: current platform)')
    parser.add_argument('--build-dir', type=Path, default=Path.cwd(),
                       help='Build directory (default: current directory)')

    args = parser.parse_args()

    # Set build directory
    build_dir = args.build_dir.resolve()
    if not build_dir.exists():
        print(f"Error: Build directory does not exist: {build_dir}")
        sys.exit(1)

    # Initialize builder
    builder = InstallerBuilder(build_dir)

    if args.clean:
        builder.clean_build()
        print("Build directories cleaned")
        return

    # Override platform if specified
    if args.platform:
        builder.current_platform = args.platform

    # Build installers
    try:
        builder.build_all()
    except subprocess.CalledProcessError as e:
        print(f"Error: Build failed with exit code {e.returncode}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()