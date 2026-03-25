==========
gallery-dl
==========

*gallery-dl* is a command-line program
to download image galleries and collections
from several image hosting sites
(see `Supported Sites <docs/supportedsites.md>`__).
It is a cross-platform tool
with many
`command-line <https://gdl-org.github.io/docs/options.html>`__ and
`configuration <https://gdl-org.github.io/docs/configuration.html>`__
options, as well as powerful
`file-naming capabilities <https://gdl-org.github.io/docs/formatting.html>`__.


|pypi| |discord| |build|

.. contents::


Dependencies
============

- Python_ 3.8+
- Requests_

Optional
--------

- aria2c_: Optional high-throughput HTTP downloader backend
- yt-dlp_ or youtube-dl_: HLS/DASH video downloads, ``ytdl`` integration
- FFmpeg_: Pixiv Ugoira conversion
- mkvmerge_: Accurate Ugoira frame timecodes
- PySocks_: SOCKS proxy support
- brotli_ or brotlicffi_: Brotli compression support
- zstandard_: Zstandard compression support
- PyYAML_: YAML configuration file support
- toml_: TOML configuration file support for Python<3.11
- SecretStorage_: GNOME keyring passwords for ``--cookies-from-browser``
- Psycopg_: PostgreSQL archive support
- truststore_: Native system certificate support
- Jinja_: Jinja template support


Installation
============


uv
--

The stable releases of *gallery-dl* are distributed on PyPI_ and can be
easily installed using uv_:

.. code:: bash

    uv tool install gallery-dl

To upgrade an existing installation, run:

.. code:: bash

    uv tool upgrade gallery-dl

Installing the latest dev version directly from GitHub can be done with
uv_ as well:

.. code:: bash

    uv tool install --from git+https://github.com/Donovoi/gallery-dl gallery-dl


Build from Source
-----------------

To build *gallery-dl* from a source checkout:

.. code:: bash

    git clone https://github.com/Donovoi/gallery-dl.git
    cd gallery-dl/
    make
    uv build

This generates the auto-created man pages, shell completion files, and docs
with :code:`make`, and then creates the source and wheel distributions in the
``dist/`` directory.

To install the project locally from the checkout instead of building release
artifacts:

.. code:: bash

    uv venv
    uv pip install --python .venv .

To install the project from a source checkout together with all optional
Python dependencies, run:

.. code:: bash

    uv venv && uv pip install --python .venv ".[extra,video]"

This installs *gallery-dl* with its ``extra`` and ``video`` extras. If you
prefer the existing Make target, it is equivalent to:

.. code:: bash

    make install-deps

This installs all optional Python packages listed above, including support for
SOCKS proxies, YAML/TOML configs, Brotli/Zstandard compression, PostgreSQL
archives, Jinja templates, and ``yt-dlp``.

To let *gallery-dl* install all optional README dependencies automatically,
including ``aria2c``, ``ffmpeg``, and ``mkvmerge`` where supported, run:

.. code:: bash

    gallery-dl --install-deps

This command is idempotent, skips dependencies that are already available, and
prints progress while it installs missing items without prompting for input.

To install the optional external tools together with the Python dependencies in
one command from a source checkout, use one of these platform-specific
commands:

Debian / Ubuntu
^^^^^^^^^^^^^^^^

.. code:: bash

    sudo apt-get update && sudo apt-get install -y aria2 ffmpeg mkvtoolnix && uv venv && uv pip install --python .venv ".[extra,video]"

macOS / Homebrew
^^^^^^^^^^^^^^^^

.. code:: bash

    brew install aria2 ffmpeg mkvtoolnix && uv venv && uv pip install --python .venv ".[extra,video]"

To build a standalone executable with Nuitka, install Nuitka together
with the optional runtime packages you want bundled and run:

.. code:: bash

    uv venv
    uv pip install --python .venv nuitka requests[socks] yt-dlp[default] pyyaml
    make
    uv run --python .venv scripts/pyinstaller.py

This writes a compiled executable to the ``dist/`` directory. On Linux
and macOS the generated file is typically named ``gallery-dl``; on
Windows Nuitka appends ``.exe`` automatically.


Standalone Executable
---------------------

Prebuilt releases with a Python interpreter and required Python
packages included are available from:

- Stable upstream releases from `mikf/gallery-dl
  <https://github.com/mikf/gallery-dl/releases>`__, which currently
  publish:

  - `Windows <https://github.com/mikf/gallery-dl/releases/latest/download/gallery-dl.exe>`__
    (Requires `Microsoft Visual C++ Redistributable Package (x64) <https://aka.ms/vs/17/release/vc_redist.x64.exe>`__)
  - `Linux <https://github.com/mikf/gallery-dl/releases/latest/download/gallery-dl.bin>`__

- Fork prereleases from `Donovoi/gallery-dl
  <https://github.com/Donovoi/gallery-dl/releases>`__ for each push to
  the ``master`` branch, including Nuitka standalone builds for Windows
  x64 and x86, Linux x64 and arm64, and macOS x64 and arm64.

Windows builds require the Microsoft Visual C++ Redistributable Package:
`x64 <https://aka.ms/vs/17/release/vc_redist.x64.exe>`__ or
`x86 <https://aka.ms/vs/17/release/vc_redist.x86.exe>`__.

Run the downloaded or freshly built executable exactly like the Python
entry point:

.. code:: bash

    ./gallery-dl_linux URL

Downloaded fork prerelease files keep their platform label, for example
``gallery-dl_linux``, ``gallery-dl_linux_arm64``, ``gallery-dl_macos``,
``gallery-dl_macos_arm64``, ``gallery-dl_windows.exe``, and
``gallery-dl_windows_x86.exe``. On Windows, run the matching ``.exe``
from ``cmd.exe`` or PowerShell. On Linux and macOS, mark the downloaded
file executable first with ``chmod +x ./gallery-dl_*`` and then run the
matching file directly, or rename it to ``gallery-dl`` first.


Nightly Builds
--------------

| Releases for each push to the ``master`` branch are published at
| https://github.com/Donovoi/gallery-dl/releases
| and include a universal ``py3-none-any`` wheel plus a source archive
| for Python environments on 64-bit ARM mobile devices such as Samsung
| Galaxy, Google Pixel, and similar Android hardware. If Termux reports
| ``cannot execute: required file not found`` for ``gallery-dl_linux_arm64``,
| use the Python package below instead of the Linux arm64 standalone
| binary.

To download the latest development version on Termux or another Android
Python environment, install it, and run gallery-dl immediately:

.. code:: bash

    python3 -m pip install --user "gallery-dl @ https://github.com/Donovoi/gallery-dl/archive/refs/heads/master.zip" && python3 -m gallery_dl URL

To download the latest mobile build with uv_, install it, and add
gallery-dl to ``PATH`` for the current and future shells:

.. code:: bash

    WHEEL="$(
      uv run python - <<'PY'
      import json
      from pathlib import Path
      from urllib.request import urlopen, urlretrieve

      with urlopen("https://api.github.com/repos/Donovoi/gallery-dl/releases") as response:
          releases = json.load(response)

      asset = next(
          (
              asset
              for release in releases
              if release["prerelease"]
              for asset in release["assets"]
              if asset["name"].endswith("-py3-none-any.whl")
          ),
          None,
      )
      if asset is None:
          raise SystemExit(
              "could not find a mobile py3-none-any wheel in the latest prerelease builds"
          )

      path = Path.home() / ".cache" / "gallery-dl" / asset["name"]
      path.parent.mkdir(parents=True, exist_ok=True)
      urlretrieve(asset["browser_download_url"], path)
      print(path)
      PY
    )" && \
    (uv tool uninstall gallery-dl >/dev/null 2>&1 || true) && \
    uv tool install "$WHEEL" && \
    BIN_DIR="$(uv tool dir --bin)" && \
    PATH_LINE="$(printf 'export PATH="%s:$PATH"' "$BIN_DIR")" && \
    export PATH="$BIN_DIR:$PATH" && \
    { grep -qsF "$BIN_DIR" "$HOME/.profile" || printf '%s\n' "$PATH_LINE" >> "$HOME/.profile"; }

If your shell uses a startup file other than ``~/.profile`` (for example,
``~/.bashrc`` or ``~/.zshrc``), add the same ``export PATH=...`` line there
instead.

After that, run ``gallery-dl URL`` normally.


Snap
----

Linux users that are using a distro that is supported by Snapd_ can install *gallery-dl* from the Snap Store:

.. code:: bash

    snap install gallery-dl


Chocolatey
----------

Windows users that have Chocolatey_ installed can install *gallery-dl* from the Chocolatey Community Packages repository:

.. code:: powershell

    choco install gallery-dl


Scoop
-----

*gallery-dl* is also available in the Scoop_ "main" bucket for Windows users:

.. code:: powershell

    scoop install gallery-dl

Homebrew
--------

For macOS or Linux users using Homebrew:

.. code:: bash

    brew install gallery-dl

MacPorts
--------

For macOS users with MacPorts:

.. code:: bash

    sudo port install gallery-dl

Docker
--------
Using the Dockerfile in the repository:

.. code:: bash

    git clone https://github.com/Donovoi/gallery-dl.git
    cd gallery-dl/
    docker build -t gallery-dl:latest .

Pulling image from `Docker Hub <https://hub.docker.com/r/Donovoi123/gallery-dl>`__:

.. code:: bash

    docker pull Donovoi123/gallery-dl
    docker tag Donovoi123/gallery-dl gallery-dl

Pulling image from `GitHub Container Registry <https://github.com/Donovoi/gallery-dl/pkgs/container/gallery-dl>`__:

.. code:: bash

    docker pull ghcr.io/Donovoi/gallery-dl
    docker tag ghcr.io/Donovoi/gallery-dl gallery-dl

Pulling *Nightly Build* images built from the latest commit by using the ``dev`` tag:

.. code:: bash

    docker pull Donovoi123/gallery-dl:dev
    docker pull ghcr.io/Donovoi/gallery-dl:dev

To run the container you will probably want to attach some directories on the host so that the config file and downloads can persist across runs.

Make sure to either download the example config file reference in the repo and place it in the mounted volume location or touch an empty file there.

If you gave the container a different tag or are using podman then make sure you adjust.  Run ``docker image ls`` to check the name if you are not sure.

This will remove the container after every use so you will always have a fresh environment for it to run. If you setup a ci-cd pipeline to autobuild the container you can also add a ``--pull=newer`` flag so that when you run it docker will check to see if there is a newer container and download it before running.

.. code:: bash

    docker run --rm  -v $HOME/Downloads/:/gallery-dl/ -v $HOME/.config/gallery-dl/gallery-dl.conf:/etc/gallery-dl.conf -it gallery-dl:latest

You can also add an alias to your shell for "gallery-dl" or create a simple bash script and drop it somewhere in your $PATH to act as a shim for this command.

Nix and Home Manager
--------------------------

Adding *gallery-dl* to your system environment:

.. code:: nix

    environment.systemPackages = with pkgs; [
      gallery-dl
    ];

Using :code:`nix-shell`

.. code:: bash

    nix-shell -p gallery-dl

.. code:: bash

    nix-shell -p gallery-dl --run "gallery-dl <args>"

For Home Manager users, you can manage *gallery-dl* declaratively:

.. code:: nix

    programs.gallery-dl = {
      enable = true;
      settings = {
        extractor.base-directory = "~/Downloads";
      };
    };

Alternatively, you can just add it to :code:`home.packages` if you don't want to manage it declaratively:

.. code:: nix

    home.packages = with pkgs; [
      gallery-dl
    ];

After making these changes, simply rebuild your configuration and open a new shell to have *gallery-dl* available.

Usage
=====

To use *gallery-dl* simply call it with the URLs you wish to download images
from:

.. code:: bash

    gallery-dl [OPTIONS]... URLS...

Use :code:`gallery-dl --help` or see `<docs/options.md>`__
for a full list of all command-line options.


Examples
--------

Download images; in this case from danbooru via tag search for 'bonocho':

.. code:: bash

    gallery-dl "https://danbooru.donmai.us/posts?tags=bonocho"


Get the direct URL of an image from a site supporting authentication with username & password:

.. code:: bash

    gallery-dl -g -u "<username>" -p "<password>" "https://twitter.com/i/web/status/604341487988576256"


Filter manga chapters by chapter number and language:

.. code:: bash

    gallery-dl --chapter-filter "10 <= chapter < 20" -o "lang=fr" "https://mangadex.org/title/59793dd0-a2d8-41a2-9758-8197287a8539"


| Search a remote resource for URLs and download images from them:
| (URLs for which no extractor can be found will be silently ignored)

.. code:: bash

    gallery-dl "r:https://pastebin.com/raw/FLwrCYsT"


If a site's address is nonstandard for its extractor, you can prefix the URL with the
extractor's name to force the use of a specific extractor:

.. code:: bash

    gallery-dl "tumblr:https://sometumblrblog.example"


Configuration
=============

Configuration files for *gallery-dl* use a JSON-based file format.


Documentation
-------------

A list of all available configuration options and their descriptions
can be found at `<https://gdl-org.github.io/docs/configuration.html>`__.

| For a default configuration file with available options set to their
  default values, see `<docs/gallery-dl.conf>`__.

| For a commented example with more involved settings and option usage,
  see `<docs/gallery-dl-example.conf>`__.


HTTP Downloader Backend (aria2c)
--------------------------------

*gallery-dl* can optionally use `aria2c`_ as its HTTP downloader for
eligible single-file downloads.

This is useful when you want aria2c's multi-connection transfer behavior
while keeping *gallery-dl*'s normal extraction and naming logic.
The built-in downloader remains the default, and *gallery-dl* falls back to
it automatically for downloads that need direct response handling.

1. Enable it in your config file:

.. code:: json

    {
        "downloader": {
            "http": {
                "aria2c": true
            }
        }
    }

If ``aria2c`` is not on your ``PATH``, you can also set the absolute path to
the executable instead of ``true``. When ``aria2c`` is enabled but missing,
*gallery-dl* will also try to install it automatically before falling back to
the built-in HTTP downloader.

See
`downloader.http.aria2c <https://gdl-org.github.io/docs/configuration.html#downloader-http-aria2c>`__
for the full option reference, tuning details, and fallback behavior.


Locations
---------

*gallery-dl* searches for configuration files in the following places:

Windows:
    * ``%APPDATA%\gallery-dl\config.json``
    * ``%USERPROFILE%\gallery-dl\config.json``
    * ``%USERPROFILE%\gallery-dl.conf``

    (``%USERPROFILE%`` usually refers to a user's home directory,
    i.e. ``C:\Users\<username>\``)

Linux, macOS, etc.:
    * ``/etc/gallery-dl.conf``
    * ``${XDG_CONFIG_HOME}/gallery-dl/config.json``
    * ``${HOME}/.config/gallery-dl/config.json``
    * ``${HOME}/.gallery-dl.conf``

When run as `executable <Standalone Executable_>`__,
*gallery-dl* will also look for a ``gallery-dl.conf`` file
in the same directory as said executable.

It is possible to use more than one configuration file at a time.
In this case, any values from files after the first will get merged
into the already loaded settings and potentially override previous ones.


Authentication
==============

Username & Password
-------------------

Some extractors require you to provide valid login credentials in the form of
a username & password pair. This is necessary for
``nijie``
and optional for
``aryion``,
``danbooru``,
``e621``,
``exhentai``,
``idolcomplex``,
``imgbb``,
``inkbunny``,
``mangadex``,
``mangoxo``,
``pillowfort``,
``sankaku``,
``subscribestar``,
``tapas``,
``tsumino``,
``twitter``,
and ``zerochan``.

You can set the necessary information in your
`configuration file <Configuration_>`__

.. code:: json

    {
        "extractor": {
            "twitter": {
                "username": "<username>",
                "password": "<password>"
            }
        }
    }

or you can provide them directly via the
:code:`-u/--username` and :code:`-p/--password` or via the
:code:`-o/--option` command-line options

.. code:: bash

    gallery-dl -u "<username>" -p "<password>" "URL"
    gallery-dl -o "username=<username>" -o "password=<password>" "URL"


Cookies
-------

For sites where login with username & password is not possible due to
CAPTCHA or similar, or has not been implemented yet, you can use the
cookies from a browser login session and input them into *gallery-dl*.

This can be done via the
`cookies <https://gdl-org.github.io/docs/configuration.html#extractor-cookies>`__
option in your configuration file by specifying

- | the path to a Mozilla/Netscape format cookies.txt file exported by a browser addon
  | (e.g. `Get cookies.txt LOCALLY <https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc>`__ for Chrome,
    `Export Cookies <https://addons.mozilla.org/en-US/firefox/addon/export-cookies-txt/>`__ for Firefox)

- | a list of name-value pairs gathered from your browser's web developer tools
  | (in `Chrome <https://developers.google.com/web/tools/chrome-devtools/storage/cookies>`__,
     in `Firefox <https://developer.mozilla.org/en-US/docs/Tools/Storage_Inspector>`__)

- | the name of a browser to extract cookies from
  | (supported browsers are Chromium-based ones, Firefox, and Safari)

For example:

.. code:: json

    {
        "extractor": {
            "instagram": {
                "cookies": "$HOME/path/to/cookies.txt"
            },
            "patreon": {
                "cookies": {
                    "session_id": "K1T57EKu19TR49C51CDjOJoXNQLF7VbdVOiBrC9ye0a"
                }
            },
            "twitter": {
                "cookies": ["firefox"]
            }
        }
    }

| You can also specify a cookies.txt file with
  the :code:`--cookies` command-line option
| or a browser to extract cookies from with :code:`--cookies-from-browser`:

.. code:: bash

    gallery-dl --cookies "$HOME/path/to/cookies.txt" "URL"
    gallery-dl --cookies-from-browser firefox "URL"


OAuth
-----

*gallery-dl* supports user authentication via OAuth_ for some extractors.
This is necessary for
``pixiv``
and optional for
``deviantart``,
``flickr``,
``reddit``,
``smugmug``,
``tumblr``,
and ``mastodon`` instances.

Linking your account to *gallery-dl* grants it the ability to issue requests
on your account's behalf and enables it to access resources which would
otherwise be unavailable to a public user.

To do so, start by invoking it with ``oauth:<sitename>`` as an argument.
For example:

.. code:: bash

    gallery-dl oauth:flickr

You will be sent to the site's authorization page and asked to grant read
access to *gallery-dl*. Authorize it and you will be shown one or more
"tokens", which should be added to your configuration file.

To authenticate with a ``mastodon`` instance, run *gallery-dl* with
``oauth:mastodon:<instance>`` as argument. For example:

.. code:: bash

    gallery-dl oauth:mastodon:pawoo.net
    gallery-dl oauth:mastodon:https://mastodon.social/


.. _Python:     https://www.python.org/downloads/
.. _PyPI:       https://pypi.org/
.. _uv:         https://docs.astral.sh/uv/
.. _Requests:   https://requests.readthedocs.io/en/latest/
.. _aria2c:     https://aria2.github.io/
.. _FFmpeg:     https://www.ffmpeg.org/
.. _mkvmerge:   https://www.matroska.org/downloads/mkvtoolnix.html
.. _yt-dlp:     https://github.com/yt-dlp/yt-dlp
.. _youtube-dl: https://ytdl-org.github.io/youtube-dl/
.. _PySocks:    https://pypi.org/project/PySocks/
.. _brotli:     https://github.com/google/brotli
.. _brotlicffi: https://github.com/python-hyper/brotlicffi
.. _zstandard:  https://github.com/indygreg/python-zstandard
.. _PyYAML:     https://pyyaml.org/
.. _toml:       https://pypi.org/project/toml/
.. _SecretStorage: https://pypi.org/project/SecretStorage/
.. _Psycopg:    https://www.psycopg.org/
.. _truststore: https://truststore.readthedocs.io/en/latest/
.. _Jinja:      https://jinja.palletsprojects.com/
.. _Snapd:      https://docs.snapcraft.io/installing-snapd
.. _OAuth:      https://en.wikipedia.org/wiki/OAuth
.. _Chocolatey: https://chocolatey.org/install
.. _Scoop:      https://scoop.sh/

.. |pypi| image:: https://img.shields.io/pypi/v/gallery-dl?logo=pypi&label=PyPI
    :target: https://pypi.org/project/gallery-dl/

.. |build| image:: https://github.com/Donovoi/gallery-dl/actions/workflows/tests.yml/badge.svg
    :target: https://github.com/Donovoi/gallery-dl/actions

.. |gitter| image:: https://badges.gitter.im/gallery-dl/main.svg
    :target: https://gitter.im/gallery-dl/main

.. |discord| image:: https://img.shields.io/discord/1067148002722062416?logo=discord&label=Discord&color=blue
    :target: https://discord.gg/rSzQwRvGnE
