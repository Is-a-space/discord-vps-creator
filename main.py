import logging
import subprocess
import sys
import os
import re
import time
import concurrent.futures
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
import docker
from colorama import Fore, Style, init

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def check_os():
    try:
        with open('/etc/os-release') as f:
            os_info = f.readlines()

            os_details = {}
            for line in os_info:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os_details[key] = value.strip('"')

            os_id = os_details.get('ID', '').lower()

            if os_id in ['ubuntu', 'debian', 'alpine']:
                logging.info(f"Operating system detected: {os_id.capitalize()}")
            else:
                logging.info("Operating system is not Ubuntu, Debian, or Alpine. Please run this code in either of those distros before rerunning this code.")
                sys.exit(0)
    except FileNotFoundError:
        logging.error("The /etc/os-release file does not exist on this system.")
        sys.exit(0)
    except Exception as e:
        logging.error(f"An error occurred while checking the OS: {e}")
        sys.exit(0)

check_os()

def install_and_import(package, version):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", f"{package}=={version}"])

packages = {
    "discord.py": "2.4.0",
    "docker": "7.1.0",
    "python-dotenv": "1.0.1",
    "colorama": "0.4.6"
}

for package, version in packages.items():
    install_and_import(package, version)

load_dotenv()
init(autoreset=True)

TOKEN = os.getenv('TOKEN')
RAM_LIMIT = os.getenv('RAM_LIMIT')
CORES=os.getenv('CPU_LIMIT')
STORAGE_LIMIT=os.getenv('STORAGE_LIMIT')

logging.info(f"{Fore.WHITE}{Style.BRIGHT}Specified Specs for VPS Creation: {Style.RESET_ALL}" + str(RAM_LIMIT) + " RAM, " + str(CORES) + " cores, " + str(STORAGE_LIMIT) + " storage")

intents = discord.Intents.all()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

def check_docker():
    try:
        client = docker.from_env()
        client.version()
        logging.info("Docker is installed and running.")
    except docker.errors.DockerException as e:
        logging.warning("Error! Docker is not installed or not started. Please install Docker or start Docker before running this again.")
        sys.exit(0)

check_docker()

client = docker.from_env()

SERVER_LIMIT = 12
database_file = 'database.txt'

executor = concurrent.futures.ThreadPoolExecutor(max_workers=150)

def add_to_database(user, container_name, ssh_command):
    with open(database_file, 'a') as f:
        f.write(f"{user}|{container_name}|{ssh_command}\n")

def remove_from_database(ssh_command):
    if not os.path.exists(database_file):
        return
    with open(database_file, 'r') as f:
        lines = f.readlines()
    with open(database_file, 'w') as f:
        for line in lines:
            if ssh_command not in line:
                f.write(line)

def get_user_servers(user):
    if not os.path.exists(database_file):
        return []
    servers = []
    with open(database_file, 'r') as f:
        for line in f:
            if line.startswith(user):
                servers.append(line.strip())
    return servers

def count_user_servers(user):
    return len(get_user_servers(user))

@bot.event
async def on_ready():
    change_status.start()
    print(f'Bot is ready. Logged in as {bot.user}')
    await bot.tree.sync()

@tasks.loop(minutes=1)
async def change_status():
    await bot.change_presence(activity=discord.Game(name="with VPS(s)"))

@bot.tree.command(name="list", description="Lists all your servers")
async def list_servers(interaction: discord.Interaction):
    user = str(interaction.user)
    servers = get_user_servers(user)
    if servers:
        embed = discord.Embed(title="Your Servers", color=0x00ff00)
        for server in servers:
            _, container_name, _ = server.split('|')
            embed.add_field(name=container_name, value="Type: Dedicated Docker Conatainer ", inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(embed=discord.Embed(description="You have no servers.", color=0xff0000))

@bot.tree.command(name="help", description="Shows the help message")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="Help", color=0x00ff00)
    embed.add_field(name="/deploy-ubuntu", value="Creates a new server with Ubuntu 22.04", inline=False)
    embed.add_field(name="/deploy-debian", value="Creates a new server with Debian 12", inline=False)
    embed.add_field(name="/deploy-arch", value="Creates a new server with Arch Linux", inline=False)
    embed.add_field(name="/remove <ssh_command/Name>", value="Removes a server", inline=False)
    embed.add_field(name="/restart <ssh_command/Name>", value="Restart a server (Disabled. Broken)", inline=False)
    embed.add_field(name="/start <ssh_command/Name>", value="Start a server (Disabled. Broken)", inline=False)
    embed.add_field(name="/stop <ssh_command/Name>", value="Stop a server (Disabled. Broken)", inline=False)
    embed.add_field(name="/ressh <ssh_command/Name>", value="Fix's SSH. However restart is recommanded. (Disabled. Broken)", inline=False)
    embed.add_field(name="/list", value="List all your server", inline=False)
    embed.add_field(name="/support", value="Provides support server link", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="support", description="Provides support server link")
async def support(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(description="Join our support server: https://discord.gg/is-a-space", color=0x00ff00))

async def get_ssh_session_line(container):
    def get_ssh_session(logs):
        match = re.search(r'ssh session: (ssh [^\n]+)', logs)
        if match and "ro-" not in match.group(1):
            return match.group(1)
        return None

    ssh_session_line = None
    max_attempts = 300000
    attempt = 0

    while attempt < max_attempts:
        logs = container.logs().decode('utf-8')
        ssh_session_line = get_ssh_session(logs)
        if ssh_session_line:
            break
        attempt += 1

    return ssh_session_line

async def create_server_task(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(description="Creating server, This takes a few seconds.\n```running apt update\nrunning apt install tmate -y\nrunning tmate -F```", color=0x00ff00))
    user = str(interaction.user)
    if count_user_servers(user) >= SERVER_LIMIT:
        await interaction.followup.send(embed=discord.Embed(description="Error: Server Limit-reached\n\nLog: ```Failed to run apt update\nFailed to run apt install tmate\nFailed to run tmate -F\nError: Server Limit-reached```", color=0xff0000))
        return

    image = "ubuntu:22.04"
    commands = """
    apt update && \
    apt install -y tmate && \
    tmate -F
    """

    container = client.containers.run(
        image, 
        command="sh -c '{}'".format(commands), 
        detach=True, 
        tty=True, 
        mem_limit=RAM_LIMIT, 
    )

    ssh_session_line = await get_ssh_session_line(container)
    if ssh_session_line:
        await interaction.user.send(embed=discord.Embed(description=f"### Successfully created VPS\n SSH Session Command: ```{ssh_session_line}```Powered by [is-a.space](https://discord.gg/is-a-space)\nOS:Ubuntu 22.04", color=0x00ff00))
        add_to_database(user, container.name, ssh_session_line)
        await interaction.followup.send(embed=discord.Embed(description="Server created successfully. Check your DMs for details.", color=0x00ff00))
    else:
        await interaction.followup.send(embed=discord.Embed(description="Something went wrong or the server is taking longer than expected. if this problem continues, Contact Support.", color=0xff0000))
        container.stop()
        container.remove()

async def create_server_task_debian(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(description="Creating server, This takes a few seconds.\n```running apt update\nrunning apt install tmate -y\nrunning tmate -F```", color=0x00ff00))
    user = str(interaction.user)
    if count_user_servers(user) >= SERVER_LIMIT:
        await interaction.followup.send(embed=discord.Embed(description="Error: Server Limit-reached\n\nLog: ```Failed to run apt update\nFailed to run apt install tmate\nFailed to run tmate -F\nError: Server Limit-reached```", color=0xff0000))
        return

    image = "debian:12"
    commands = """
    apt update && \
    apt install -y tmate && \
    tmate -F
    """

    container = client.containers.run(
        image, 
        command="sh -c '{}'".format(commands), 
        detach=True, 
        tty=True, 
        mem_limit=RAM_LIMIT,
    )

    ssh_session_line = await get_ssh_session_line(container)
    if ssh_session_line:
        await interaction.user.send(embed=discord.Embed(description=f"### Successfully created VPS\n SSH Session Command: ```{ssh_session_line}```Powered by [is-a.space](https://discord.gg/is-a-space)\nOS:Debian 12", color=0x00ff00))
        add_to_database(user, container.name, ssh_session_line)
        await interaction.followup.send(embed=discord.Embed(description="Server created successfully. Check your DMs for details.", color=0x00ff00))
    else:
        await interaction.followup.send(embed=discord.Embed(description="Something went wrong or the server is taking longer than expected. if this problem continues, Contact Support.", color=0xff0000))
        container.stop()
        container.remove()

async def create_server_task_arch(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(description="Creating server, This takes a few seconds.\n```running pacman -Sy\nrunning pacman -S tmate\nrunning tmate -F```", color=0x00ff00))
    user = str(interaction.user)
    if count_user_servers(user) >= SERVER_LIMIT:
        await interaction.followup.send(embed=discord.Embed(description="Error: Server Limit-reached\n\nLog: ```Failed to run pacman -Sy\nFailed to run pacman -S tmate\nFailed to run tmate -F\nError: Server Limit-reached```", color=0xff0000))
        return

    image = "archlinux:latest"
    commands = """
    pacman -Sy --noconfirm && \
    pacman -S --noconfirm tmate && \
    tmate -F
    """

    container = client.containers.run(
        image, 
        command="sh -c '{}'".format(commands), 
        detach=True, 
        tty=True, 
        mem_limit=RAM_LIMIT,
    )

    ssh_session_line = await get_ssh_session_line(container)
    if ssh_session_line:
        await interaction.user.send(embed=discord.Embed(description=f"### Successfully created VPS\n SSH Session Command: ```{ssh_session_line}```Powered by [is-a.space](https://discord.gg/is-a-space)\nOS:Arch Linux", color=0x00ff00))
        add_to_database(user, container.name, ssh_session_line)
        await interaction.followup.send(embed=discord.Embed(description="Server created successfully. Check your DMs for details.", color=0x00ff00))
    else:
        await interaction.followup.send(embed=discord.Embed(description="Something went wrong or the server is taking longer than expected. if this problem continues, Contact Support.", color=0xff0000))
        container.stop()
        container.remove()

@bot.tree.command(name="deploy-ubuntu", description="Creates a new server with Ubuntu 22.04")
async def deploy_ubuntu(interaction: discord.Interaction):
    await create_server_task(interaction)

@bot.tree.command(name="deploy-debian", description="Creates a new server with Debian 12")
async def deploy_debian(interaction: discord.Interaction):
    await create_server_task_debian(interaction)

@bot.tree.command(name="deploy-arch", description="Creates a new server with Arch Linux")
async def deploy_arch(interaction: discord.Interaction):
    await create_server_task_arch(interaction)

async def start_server_task(interaction: discord.Interaction, ssh_command_or_name: str):
    user = str(interaction.user)
    servers = get_user_servers(user)
    client = docker.from_env()

    for server in servers:
        _, container_name, ssh_command = server.split('|')
        if ssh_command == ssh_command_or_name or container_name == ssh_command_or_name:
            try:
                container = client.containers.get(container_name)
                if container.status != 'running':
                    logging.info(f"Starting container: {container_name}")
                    container.start()
                    container.reload()
                    if container.status != 'running':
                        raise Exception(f"Failed to start the container {container_name}.")
                else:
                    logging.info(f"Container {container_name} is already running. Restarting")
                    container.stop()
                    container.reload()

                if container.status != 'exited':
                        raise Exception(f"Failed to stop the container {container_name}.")
                container.start()
                container.reload()
                if container.status != 'running':
                    raise Exception(f"Failed to start the container {container_name}.")

                commands = "tmate -F"
                exec_result = container.exec_run(f'sh -c "{commands}"', detach=True, tty=True)

                if exec_result.exit_code != 0:
                    raise Exception(f"Failed to start SSH session with exit code {exec_result.exit_code}.")

                ssh_session_line = await get_ssh_session_line(container)
                if ssh_session_line:
                    await interaction.response.send_message(embed=discord.Embed(description=f"Server started successfully. SSH command: {ssh_session_line}", color=0x00ff00))
                    await interaction.followup.send(embed=discord.Embed(description="Server created successfully. Check your DMs for details.", color=0x00ff00))
                else:
                    raise Exception("Unable to retrieve SSH session line.")
            except Exception as e:
                error_message = f"Failed to start server: Unable to execute SSH command. Error: {str(e)}"
                logging.error(error_message)
                await interaction.response.send_message(embed=discord.Embed(description=error_message, color=0xff0000))
                return

    await interaction.response.send_message(embed=discord.Embed(description="Server not found.", color=0xff0000))

@bot.tree.command(name="start", description="Starts a server")
async def start_server(interaction: discord.Interaction, ssh_command_or_name: str):
    await interaction.response.send_message(embed=discord.Embed(description="Starting your server. Please wait...", color=0x00ff00))
    await start_server_task(interaction, ssh_command_or_name)

@bot.tree.command(name="stop", description="Stops a server")
async def stop_server(interaction: discord.Interaction, ssh_command_or_name: str):
    await interaction.response.send_message(embed=discord.Embed(description="Stopping your server. Please wait...", color=0x00ff00))
    user = str(interaction.user)
    servers = get_user_servers(user)
    server_found = False
    for server in servers:
        _, container_name, ssh_command = server.split('|')
        if interaction.data['options'][0]['value'] in (ssh_command, container_name):
            server_found = True
            container = client.containers.get(container_name)
            container.stop()
            await interaction.followup.send(embed=discord.Embed(description="Server stopped successfully.", color=0x00ff00))
            break
    if not server_found:
        await interaction.followup.send(embed=discord.Embed(description="Server not found. Please check your input.", color=0xff0000))

async def stop_server_task(interaction: discord.Interaction, ssh_command: str):
    user = str(interaction.user)
    servers = get_user_servers(user)
    if any(ssh_command in server for server in servers):
        container_name = next((server.split('|')[1] for server in servers if ssh_command in server), None)
        if container_name:
            try:
                container = client.containers.get(container_name)
                
                if container.status == 'running':
                    container.stop()
                    await interaction.response.send_message(embed=discord.Embed(description="Server stopped successfully.", color=0x00ff00))
                else:
                    await interaction.response.send_message(embed=discord.Embed(description="Server is not running.", color=0xff0000))
            except docker.errors.APIError as e:
                await interaction.response.send_message(embed=discord.Embed(description=f"Failed to stop server: {str(e)}", color=0xff0000))
        else:
            await interaction.response.send_message(embed=discord.Embed(description="Server not found.", color=0xff0000))
    else:
        await interaction.response.send_message(embed=discord.Embed(description="Something went wrong trying to stop this server.", color=0xff0000))@bot.tree.command(name="remove", description="Removes a server")
async def remove_server(interaction: discord.Interaction, ssh_command_or_name: str):
    user = str(interaction.user)
    servers = get_user_servers(user)
    server_found = False

    for server in servers:
        _, container_name, ssh_command = server.split('|')
        if ssh_command_or_name in (ssh_command, container_name):
            server_found = True
            container = client.containers.get(container_name)
            container.stop()
            container.remove()
            remove_from_database(ssh_command)
            await interaction.followup.send(embed=discord.Embed(description="Server removed successfully.", color=0x00ff00))
            break
    
    if not server_found:
        await interaction.followup.send(embed=discord.Embed(description="Server not found. Please check your input.", color=0xff0000))

bot.run(TOKEN)
