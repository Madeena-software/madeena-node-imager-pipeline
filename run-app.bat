@echo off
REM Batch file to start the backend from the project root
REM Usage: run-backend.bat

pushd backend
python app.py
popd
