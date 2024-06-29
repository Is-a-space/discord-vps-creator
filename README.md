# Discord Docker VPS Bot

> [!IMPORTANT]
>
> You need a Discord bot token from [Discord Developer Portal](https://discord.dev). Create a application there.
>
> If you need any support, join our support Discord and create a ticket: https://discord.gg/ctpG8apzC3

**Features**
- Quick and easy deployment using Docker
- Autodeploy SSH (You can choose either tmate or serveo. If you're using servo.net, edit the script to use this command instead:  `ssh -R $HOSTNAME:22:localhost:22 serveo.net`. We suggest tmate for better uptime.)
- Deploys Docker Containers (you can run this anywhere you want, even on a bad computer / vps!)
- Has creation / deletion / listing of servers
- Supports Debian 12 and Ubuntu 22.04 (at the moment)
- A customizeable install script and docker image that you can change easily
- Uses slash commands to enhance the user expierence
- Start/stop/restart of VPS(s)
- Spec Limiter

**Features in Progress**
- Systemctl support (+++)
- Alpine Linux Support
- Node support/shards
- A Plan system

Features
- Quick and easy deployment
- SSH (Using tmate. or using serveo.net if editing the script to use `ssh -R $HOSTNAME:22:localhost:22 serveo.net` instead of tmate -F. however tmate has more uptime)
- Uses docker (so you could use this on anything, Even your shitty ahh computer)
- Has creation and removeal and listing of servers
- Supports Debian 12 and Ubuntu 22.04
- A customizeable install script and docker image.
- Uses slash commands
- Start/stop of vps(s)

Work in progress (most likely will never happen without you guys)
- Nodeable support/Shards
- Alpine Linux Support (it exists but never works)
- Systemctl Support
- Spec Limiter

**How to create a VPS using the bot?**
- Go in any channel that has slash command permissions (if you're not owner. If you're owner / administrator you can run this in any channel)
- Make sure the bot is in your server and is online
- Run /deploy-ubuntu or /deploy-debian (based on what os you want to use) and wait as it deploys. The bot will send you a message in DMS with the SSH command.
- Open your terminal and paste the SSH command to SSH into the server.

**Requirements to use the bot**:
- Your bot host is Linux (any distro). We recommand **Ubuntu, Debian, or Alpine** as the OS to get the best preformance.
- Docker is installed on your Linux machine.
- Python 3.10 is insatlled on your Linux machine. (You can run `sudo apt install python3 python3-pip` to download Python)

**How to use**:
- Download the latest `.py` file from our [Latest Releases](https://github.com/Is-a-space/discord-vps-creator/releases/)
- Edit main.py file and look for the TOKEN line and give it your bot token, You get it from [here](<discord.dev>)
- Run the file by using `python3 v2.py`

---
If you want to see the bot in action or you are too lazy to deploy it yourself, you can invite our VPS bot [here](https://discord.com/oauth2/authorize?client_id=1249856618468737104&permissions=8&integration_type=0&scope=bot)
