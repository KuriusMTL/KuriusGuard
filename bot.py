import discord
from multicolorcaptcha import CaptchaGenerator
from io import BytesIO
from datetime import datetime, timedelta
import re

# CONFIGURATIONS
TOKEN = ''
CAPCTHA_SIZE_NUM = 1
command_roles = ["Kurius Executive", "Ambassador"] # Roles that can use commands
watch_list_length = 10
max_tries = 3
verified_role = "Verified User"
console_channel = 935607969704443946               # Channel where logs are printed
command_channel = console_channel                  # Channel where commands are sent
server_id = 692133317520261120                     # Kurius Discord Server

# Init Discord client
client = discord.Client(intents=discord.Intents.all())
# Init captcha creator
captcha = CaptchaGenerator(CAPCTHA_SIZE_NUM)

# Runtime cache
watch_list = [] # Name, date joined, ID
captcha_list = {} # ID, {captcha answer, tries}
stop_flagging = False

''' 
The following method is executed when a user joins the user
'''

@client.event
async def on_ready():
    await print_to_console(f'{client.user} is up and running.')

'''
The following method is executed when a message is sent by a user
'''

@client.event
async def on_message(message):
    global stop_flagging

    # Ignore messages from self
    if message.author == client.user: return

    # Determine if the message was sent from the server or from a DM
    if isinstance(message.channel, discord.DMChannel): 
        # Channel is a DM so we need to check if the user is in the watch list

        # There was no captcha sent to this user yet
        if message.author.id not in captcha_list: return

        # Verify captcha answer input
        if message.content == captcha_list[message.author.id]["answer"]: 

            # Correct captcha answer
            await print_to_console(f"{message.author.name} got the captcha right and is now verified.")
            await message.channel.send("Thank you! You are now verified and can access the server. Please visit #introduce-yourself and #self-assign-roles to get started.")

            # Provide verified role to user
            server = client.get_guild(server_id)
            user = get_user_from_server(message.author.id)
            if user is not None: 
                await user.add_roles(discord.utils.get(server.roles, name=verified_role)) # Give verified role

                # Give previous roles to user
                for role in captcha_list[message.author.id]["roles"]:
                    await user.add_roles(discord.utils.get(server.roles, name=role))

            captcha_list.pop(message.author.id) # Remove captcha from cache
            return
        
        # Incorrect captcha answer
        tries = captcha_list[message.author.id]["tries"] # Get the number of tries left

        if tries <= 0: # User has failed to respond to captchas too many times
            await message.channel.send("You have exceeded the maximum number of tries. Please contact one of our Community Managers (NextLight#1378, Fred#5920, or Orius#0813).")
            await print_to_console(f'{message.author.name} has failed the captcha {max_tries} times.')
            return
        
        tries -= 1 # Decrease number of tries left

        # Captcha is incorrect, but because the user still has tries left, send another captcha
        await message.channel.send(f"Incorrect answer. You have {tries} more tries left. Here is a new captcha.")
        await send_captcha(message.author, tries) # Send new captcha
        return
    
    # Channel is a server channel
    # Check if the user has authority to execute the following commands
    if [role.name for role in message.author.roles if role.name in command_roles] != []:

        # Check if the command is sent in the command channel
        if message.channel.id == command_channel:

            # Parse input command
            commands = message.content.split(" ")

            # Give everyone the verified role
            # Should only be used when initializing the bot for the first time
            if commands[0] == "!verifyall":
                await print_to_console("Verifying all users... Please wait. This may take a while.")

                # Get all users in the server and give them the verified role
                for user in message.guild.members:
                    await user.add_roles(discord.utils.get(message.guild.roles, name=verified_role))

                await print_to_console("Gave verified role to all members of the server.")
                return

            # Give Verified User role from ID
            # Syntax !verify <user ID>
            if commands[0] == "!verify":

                # Verify if the user was provided
                if len(commands) < 2: await print_to_console("Please provide a user ID.")

                try:
                    # Get the user from the server
                    user_id = int(commands[1])
                    user = get_user_from_server(user_id)

                    # Add verified role to user
                    await user.add_roles(discord.utils.get(message.guild.roles, name=verified_role))

                    # Remove user from captcha list
                    captcha_list.pop(user_id)

                    await print_to_console(f"Manually verified {user.name} with success.")
                except Exception:
                    await print_to_console(f"\"{commands[1]}\" is no valid user ID.")
                return
            
            # Flag user manually by ID
            # Syntax: !flag <user ID>
            if commands[0] == "!flag":

                # Verify if the user was provided
                if len(commands) < 2: await print_to_console("Please provide a user ID.")

                try:
                    # Get the user bu ID
                    user = await client.fetch_user(commands[1])

                    # Remove previous verified role if user has it
                    try:
                        await user.remove_roles(discord.utils.get(user.guild.roles, name=verified_role))
                    except:
                        pass

                    # Send captcha to user
                    await send_captcha(user)
                    await print_to_console(f"Sent a captcha to {user.name}. Awaiting a response.")
                    return

                except:
                    await print_to_console(f"\"{commands[1]}\" is no valid user ID.")
                    return

            # Disable auto flagging users
            # Syntax: !ignore enable/disable
            if commands[0] == "!ignore":

                # Verify if the command was provided
                if len(commands) < 2: await print_to_console("Please provide a valid command. Valid commands are: enable, disable.")

                if commands[1] == "enable":
                    stop_flagging = True
                    await print_to_console(f"Stopped auto flagging users.")
                elif commands[1] == "disable":
                    stop_flagging = False
                    await print_to_console(f"Started auto flagging users.")
                else:
                    await print_to_console("Please provide a valid command. Valid commands are: enable, disable.")
                return

'''
    The following method is executed when a user joins the server
'''

@client.event
async def on_member_join(member):
    if member.guild.id != server_id: return # User joined in another server the bot is in

    await print_to_console(f'{member.name} has joined the server.')

    # Check if auto flagging is enabled
    if stop_flagging:
        await print_to_console("Flagging is currently disabled. `!ignore disable` to start flagging again.")
        await member.add_roles(discord.utils.get(member.guild.roles, name=verified_role)) # Give verified role to user
        return

    # Keep track of the incoming traffic
    watch_list.append({"name": member.name, "id": member.id, "joined_at": member.joined_at}) # Add member to watch list

    # Keep the watch list length smaller than watch_list_length
    if len(watch_list) > watch_list_length: watch_list.pop(0)

    # Logic to determine if user is sus

    # Check if the username is in the blacklist
    with open("blacklist.txt", "r") as f:

        # Open blacklist file and compare each line to the username

        blacklist = f.readlines()
        if member.name in blacklist:
            await print_to_console(f"{member.name} was auto-flagged (Reason: blacklist).")
            await send_captcha(member)
            return
    
    # Check if user joined within 30 seconds of previous user
    if len(watch_list) > 1:
        if watch_list[-1]["joined_at"] - watch_list[-2]["joined_at"] < timedelta(seconds=30):

            await print_to_console(f"{member.name} was auto-flagged (Reason: joining within 30 seconds from the previous user).")
            await send_captcha(member) # Send captcha to user

            # If previous user hasn't been flagged, flag them and send captcha to them too
            if watch_list[-2]["id"] not in captcha_list.keys():
                try:
                    previous_user = get_user_from_server(watch_list[-2]["id"])
                    try:
                        await previous_user.remove_roles(discord.utils.get(member.guild.roles, name=verified_role))
                        await print_to_console(f"{previous_user.name} was auto-flagged (Reason: joining within 30 seconds from the previous user).")
                    except Exception as err:
                        await print_to_console(f"Error: {err} - While trying to flag previous user.")
                    await send_captcha(previous_user)
                except discord.NotFound:
                    await print_to_console("Previous user not found in the server.")
                except Exception as err:
                    await print_to_console("Error {err} - While trying to flag previous user")
            return
    
    # Check to see if the user's account is at least a week old
    if datetime.now() - member.created_at < timedelta(days=7):
        await print_to_console(f"{member.name} was auto-flagged (Reason: account is less than a week old).")
        await send_captcha(member)
        return

    # Check to see if the user matches a known pattern
    with open("patterns.txt", "r") as f:

        # Open patterns file and compare each line to the username

        patterns = f.readlines()
        for pattern in patterns:
            if bool(re.match(pattern, member.name)):
                await print_to_console(f"{member.name} was auto-flagged (Reason: known pattern).")
                await send_captcha(member)
                return
    
    # Check if the user has a profile pic or a status
    if member.avatar_url == member.default_avatar_url and member.activity == None:
        await print_to_console(f"{member.name} was auto-flagged (Reason: no profile pic and/or no status).")
        await send_captcha(member)
        return

    # No anomalies detected, give user verified role
    await print_to_console(f'{member.name} passed all tests and is verified.')
    await member.add_roles(discord.utils.get(member.guild.roles, name=verified_role)) # Give verified role to user


'''
    Send a captcha to a user.
    @param user: The user's id.
    @param tries (optional): The number of tries the user has tried to verify.
    @return answer: The captcha answer.

'''

async def send_captcha(user, tries = max_tries):
    await print_to_console(f"Sending captcha to {user.name}. Tries: {max_tries - tries}/{max_tries}")

    prev_roles = []

    # Remove verified role if user has it
    if hasattr(user, 'roles'):
        # Remove the verified role from the user
        if (discord.utils.get(user.guild.roles, name=verified_role) in user.roles): await user.remove_roles(discord.utils.get(user.guild.roles, name=verified_role))
        prev_roles = [role.name for role in user.roles] # Remember previous roles

        # Remove all roles
        for role in user.roles:
            await user.remove_roles(role)

    # Generate captcha
    bytes, answer = generate_captcha()

    # Add captcha to captcha list
    captcha_list[user.id] = {"answer": answer, "tries": tries, "roles": prev_roles}

    # Attach captcha to a discord embed
    img_file = discord.File(bytes, filename="captcha.png")
    emoji = discord.utils.get(client.emojis, name='sus')
    embed = discord.Embed(title=f"Oops, are you a robot? {str(emoji)}", description="We've noticed some anomalies with your account. There is no need to worry. Please respond with the 4 digits from the captcha to verify your identity and access the Kurius Discord server.", color=0xFF0000)
    embed.set_image(url='attachment://captcha.png')

    # Send captcha to user
    await user.send(file=img_file, embed=embed)
    return answer

'''
    Generate a new captcha and returns the bytes and the answer as a tuple
    The difficulty (size) of the captcha can be set by changing the CAPCTHA_SIZE_NUM variable.
    @returns (bytes, answer)
'''

def generate_captcha():

    # Generate captcha
    captcha_data = captcha.gen_captcha_image(difficult_level=3)
    image = captcha_data["image"]
    characters = captcha_data["characters"]

    # Crop image
    width, height = image.size
    image = image.crop((0, height/4, width, height/2 + height/4))

    # Image to binary
    bytes = BytesIO()
    image.save(bytes, format="PNG")
    bytes.seek(0)

    return bytes, characters

'''
    Get the user object from the server. A value of None is returned if the user is not found.
    The specified server can be changed by changing the server_id variable.
    @param user_id: The user id of the user
    @return: The user object
'''

def get_user_from_server(user_id):
    try:
        server = client.get_guild(server_id)    # Get the server
        user = server.get_member(user_id)       # Get the user
        return user
    except:
        return None                             # User not found

'''
    Disable discord markdown formatting
    @param message: Message to be formatted
    @return: Formatted message
'''

def sanitize_md_chars(string):
    return string.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")

'''
    Prints to local and discord channel consoles
    @param message: Message to print
'''
async def print_to_console(message):
    server = client.get_guild(server_id)                   # Get server
    channel = server.get_channel(console_channel)          # Get console channel
    await channel.send(sanitize_md_chars(message))         # Send message to console channel
    print(message)                                         # Print message to local console


if __name__ == '__main__':

    # Rum Discord bot
    client.run(TOKEN)
