# Ciklum AI Academy - Capstone project

## How to run the application
 - Pull the source code from the repository
 - Setup the virtual environment
   - Required python version: **3.10**
 - Install the packages from requirements.txt using `pip`
 - Ensure the `ffmpeg` version 7.1.3 is installed on your system and in your `PATH` env. variable
 - Run the application

### OpenWebUi setup (also explained in the video)
 - Run the required containers using `docker compose up -d`
 - Open the OpenWebUI app (defaults to `localhost:3000`)
 - Default credentials are
   - Email: michal@michal.local
   - Pass: michal
 - On the top right, click on the user profile -> Admin panel
 - In the top menu, click settings
 - In the left menu, click connections
 - Add new OpenAI API connection with URL `http://host.docker.internal:8000/v1`
   - for the authentication, select Bearer with random value
 - In the left menu, select Interface
 - For the local and external task model, select the task model configured in the config.yaml
   - defaults to `qwen/qwen3-1.7b`

That's it! Open new chat, select the configured agent chat model (default `nvidia/nemotron-3-nano`) and chat away!