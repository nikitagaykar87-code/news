@echo off
echo ===================================================
echo Preparing Git Repository ^& Pushing to GitHub
echo ===================================================
echo GitHub Username: nikitagaykar87-code
echo Repository Name: news
echo.

git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not in your system PATH.
    echo Please install Git from https://git-scm.com/ and try again.
    pause
    exit /b 1
)

echo Initializing local Git repository...
git init

echo Adding files...
git add .

echo Committing...
git commit -m "Initialize secure news portal with blended news feed and production configurations"

echo Renaming branch to main...
git branch -M main

echo Adding remote repository...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/nikitagaykar87-code/news.git

echo.
echo Pushing to GitHub...
echo (You may be prompted to authenticate in your browser)
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] Code pushed successfully to https://github.com/nikitagaykar87-code/news
) else (
    echo.
    echo [WARNING] Git push failed. Please verify that:
    echo 1. You created a repository named 'news' on your GitHub account (nikitagaykar87-code).
    echo 2. You are logged into Git on this machine.
)
pause
