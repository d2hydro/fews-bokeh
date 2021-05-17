rem setting environment to python installation
SET VIRTUAL_ENV=d:\python\envs\hydrobase
SET PATH=%VIRTUAL_ENV%;%VIRTUAL_ENV%\Library\mingw-w64\bin;%VIRTUAL_ENV%\Library\usr\bin;%VIRTUAL_ENV%\Library\bin;%VIRTUAL_ENV%\Scripts;%VIRTUAL_ENV%\bin;%PATH%

rem set bokeh secret key
set BOKEH_SECRET_KEY="RvkcyFJ4BUo9m3yTwIebOkUoxYXHW6awpjQfhAqWgoFs"
set BOKEH_SIGN_SESSIONS=true

rem serve bokeh (only access with signed session)
bokeh serve wik --port 5002 --session-ids=external-signed
