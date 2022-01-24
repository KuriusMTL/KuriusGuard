import discord
from multicolorcaptcha import CaptchaGenerator
from io import BytesIO
from datetime import datetime, timedelta
import re

TOKEN = 'OTIyNzAyMjMyODAwMDg4MDc0.YcFTaw.vBjKpJ32efB1R9ouUDkuA7D8ASw'
CAPCTHA_SIZE_NUM = 1

client = discord.Client(intents=discord.Intents.all())
captcha = CaptchaGenerator(CAPCTHA_SIZE_NUM)

watch_list_length = 10
watch_list = [] # Name, date joined, ID

max_tries = 3
captcha_list = {} # ID, {captcha answer, tries}

verified_role = "Verified User"

command_channel = 904198381734330378
server_id = 692133317520261120

stop_flagging = False

@client.event
async def on_ready():
    print(f'{client.user} is up and running.')

@client.event
async def on_message(message):
    if message.author == client.user: return

    if isinstance(message.channel, discord.DMChannel): # Channel is a DM
        if message.author.id not in captcha_list: # There was no captcha sent to this user
            return

        if message.content == captcha_list[message.author.id]["answer"]: # Correct answer to captcha
            await message.channel.send("You are now verified and can access the server.")
            captcha_list.pop(message.author.id)

            server = client.get_guild(server_id)
            user = get_user_from_server(message.author.id)
            if user is not None: await user.add_roles(discord.utils.get(server.roles, name=verified_role)) # Give verified role
            return
        
        tries = captcha_list[message.author.id]["tries"] # Get the number of tries left

        if tries <= 0: # User has failed to respond to captcha too many times
            await message.channel.send("You have exceeded the maximum number of tries. Please contact one of our Community Managers (NextLight#1378 or Fred#5920).")
            return
        
        tries -= 1
        await message.channel.send(f"Incorrect answer. You have {tries} more tries left. Here is a new captcha.")
        await send_captcha(message.author, tries) # Send new captcha and decrement tries
        return
    
    # Check if the user has authority to execute the following commands
    if "Community Manager" in [role.name for role in message.author.roles]:
        if message.channel.id == command_channel:

            # Give everyone the verified role
            # Should only be used when initializing the bot
            if message.content == "!verifyall":
                print(len(message.guild.members))
                for user in message.guild.members:
                    print("Gave role to " + user.name)
                    await user.add_roles(discord.utils.get(message.guild.roles, name=verified_role))
                print("Gave role to everyone.")
                return

            # Give Verified User role from ID
            if message.content.split(" ")[0] == "!verify":
                user_id = int(message.content.split(" ")[1])
                user = get_user_from_server(user_id)
                await user.add_roles(discord.utils.get(message.guild.roles, name=verified_role))
                captcha_list.pop(user_id)
                return
            
            # Flag user manually by ID
            # Syntax: !flag <user ID>
            if message.content.split()[0] == "!flag":
                try:
                    # Get the user bu ID
                    user = await client.fetch_user(message.content.split()[1])

                    # Remove previous verified role if user has it
                    try:
                        await user.remove_roles(discord.utils.get(user.guild.roles, name=verified_role))
                    except:
                        pass

                    # Send captcha to user
                    await send_captcha(user)
                    return

                except:
                    await message.channel.send("Invalid user ID.")
                    return

            # Stop flagging users <!ignore enable/disable>
            if message.content.split(" ")[0] == "!ignore":
                if message.content.split(" ")[1] == "enable":
                    stop_flagging = True
                elif message.content.split(" ")[1] == "disable":
                    stop_flagging = False
                return



@client.event
async def on_member_join(member):
    if stop_flagging:
        await member.add_roles(discord.utils.get(member.guild.roles, name=verified_role)) # Give verified role to user
        return

    print(f'{member} has joined the server.')
    watch_list.append({"name": member.name, "id": member.id, "joined_at": member.joined_at}) # Add member to watch list

    # Keep the watch list length smaller than watch_list_length
    if len(watch_list) > watch_list_length:
        watch_list.pop(0)

    # Logic to determine if user is sus

    # Check if the user is in the blacklist
    with open("blacklist.txt", "r") as f:
        blacklist = f.readlines()
        if member.name in blacklist:
            print("Flagged by blacklist")
            await send_captcha(member)
            return
    
    # Check if user joined within 30 seconds of previous user
    if len(watch_list) > 1:
        if watch_list[-1]["joined_at"] - watch_list[-2]["joined_at"] < timedelta(seconds=30):
            print("Flagged by joined within 30 seconds")
            await send_captcha(member) # Send captcha to user
            # if previous user hasn't been flagged, flag them and send captcha to them too
            if watch_list[-2]["id"] not in captcha_list.keys():
                try:
                    previous_user = get_user_from_server(watch_list[-2]["id"])
                    try:
                        await previous_user.remove_roles(discord.utils.get(member.guild.roles, name=verified_role))
                    except Exception as e:
                        print(e)
                    await send_captcha(previous_user)
                except discord.NotFound:
                    print("Previous user not found")
                except:
                    print("Error trying to flag previous user")
            return
    
    # Check to see if the user's account is at least a week old
    if datetime.now() - member.created_at < timedelta(days=7):
        print("Flagged by ageism")
        await send_captcha(member)
        return

    # Check to see if the user matches a known pattern
    with open("patterns.txt", "r") as f:
        patterns = f.readlines()
        for pattern in patterns:
            if bool(re.match(pattern, member.name)):
                print("Flagged by patterns")
                await send_captcha(member)
                return
    
    # Check if the user has a profile pic or a status
    if member.avatar_url == member.default_avatar_url and member.activity == None:
        print("Flagged by no profile pic and no status")
        await send_captcha(member)
        return

    await member.add_roles(discord.utils.get(member.guild.roles, name=verified_role)) # Give verified role to user


# Send the captcha to user and returns the answer to the captcha
async def send_captcha(user, tries = max_tries):
    # Remove verified role if user has it
    if hasattr(user, 'roles') and (verified_role in user.roles):
        await user.remove_roles(discord.utils.get(user.guild.roles, name=verified_role))

    bytes, answer = generate_captcha()
    img_file = discord.File(bytes, filename="captcha.png")
    emoji = discord.utils.get(client.emojis, name='sus')
    embed = discord.Embed(title=f"Oops, are you a robot? {str(emoji)}", description="We've noticed some anomalies with your account. There is no need to worry. Please respond with the 4 digits from the captcha to verify your identity and access the Kurius Discord server.", color=0xFF0000)
    embed.set_image(url='attachment://captcha.png')
    captcha_list[user.id] = {"answer": answer, "tries": tries}
    await user.send(file=img_file, embed=embed)
    return answer

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

def get_user_from_server(user_id):
    try:
        server = client.get_guild(server_id)
        user = server.get_member(user_id)
        return user
    except:
        return None
    

if __name__ == '__main__':
    client.run(TOKEN)
