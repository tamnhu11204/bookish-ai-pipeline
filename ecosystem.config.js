module.exports = {
  apps: [
    {
      name: 'bookish-ai',
      script: 'start.py',
      interpreter: 'C:\\Users\\LENOVO\\bookish-ai-pipeline\\venv\\Scripts\\python.exe',
      cwd: 'C:\\Users\\LENOVO\\bookish-ai-pipeline',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        PYTHONIOENCODING: 'utf-8',
        PYTHONLEGACYWINDOWSSTDIO: 'utf-8'
      }
    }
  ]
};