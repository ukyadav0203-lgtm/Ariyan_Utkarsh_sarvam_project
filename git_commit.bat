@echo off
set "GIT=C:\Users\UTKARSH\AppData\Local\GitHubDesktop\app-3.6.4\resources\app\git\cmd\git.exe"
cd /d "C:\Users\UTKARSH\.gemini\antigravity\scratch\sarvam-ai"
"%GIT%" add .
"%GIT%" config user.name "Utkarsh"
"%GIT%" config user.email "utkarsh@example.com"
"%GIT%" commit -m "feat: initial commit for MandiMitra voice-first APMC arbitrage engine"
"%GIT%" branch -M main
"%GIT%" status
