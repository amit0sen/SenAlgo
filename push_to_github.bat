@echo off
echo ================================================
echo  SenAlgo v2.0 - Push to GitHub
echo  by Amit Kumar Sen
echo ================================================

cd /d "%~dp0"

echo Cleaning old .git...
if exist ".git" rmdir /s /q ".git"

echo Initializing repo...
git init

echo Setting identity...
git config user.email "akperson44@gmail.com"
git config user.name "Amit Kumar Sen"

echo Staging files...
git add -A

echo Committing...
git commit -m "SenAlgo v2.0 by Amit Kumar Sen"

echo Setting remote...
git remote add origin https://github.com/amit0sen/SenAlgo.git

echo Switching to main branch...
git branch -M main

echo Pushing...
git push -u origin main --force

echo.
echo ================================================
echo  Done! https://github.com/amit0sen/SenAlgo
echo ================================================
pause
