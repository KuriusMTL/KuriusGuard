import discord
from multicolorcaptcha import CaptchaGenerator
from io import BytesIO
from datetime import datetime

TOKEN = ''
CAPCTHA_SIZE_NUM = 2

client = discord.Client(intents=discord.Intents.all())
captcha = CaptchaGenerator(CAPCTHA_SIZE_NUM)

watch_list_length = 10
watch_list = [] # Name, date joined, ID

max_tries = 3
captcha_list = {} # ID, {captcha answer, tries}

verified_role = "Verified User"

command_channel = 904198381734330378

@client.event
async def on_ready():
    print(f'{client.user} is up and running.')

@client.event
async def on_message(message):
    if message.author == client.user: return

    if isinstance(message.channel, discord.DMChannel): # Channel is a DM
        if message.author.id not in captcha_list: # There was no captcha sent to this user
            return

        if message.content == captcha_list[message.author.id]: # Correct answer to captcha
            await message.channel.send("You are now verified and can access the server.")
            captcha_list.pop(message.author.id)
            await message.author.add_roles(discord.utils.get(message.guild.roles, name=verified_role)) # Give verified role
            return
        
        tries = captcha_list[message.author.id]["tries"] # Get the number of tries left

        if tries <= 0: # User has failed to respond to captcha too many times
            await message.channel.send("You have exceeded the maximum number of tries. Please contact one of our Community Managers (NextLight#1378 or Fred#5920).")
            return
        
        tries -= 1
        await message.channel.send(f"Incorrect answer. You have {tries} more tries left. Here is a new captcha.")
        await send_captcha(message.author, tries) # Send new captcha and decrement tries
        return
    
    if "Community Manager" in message.author.roles:
        if message.channel.id == command_channel:
            # Give everyone the verified role
            # Should only be used when initializing the bot
            if message.content == "!verifyall":
                for user in message.guild.members:
                    user.add_roles(discord.utils.get(message.guild.roles, name=verified_role))
                return
            
            # Flag user manually by ID
            # Syntax: !flag <user ID>
            if message.content.split()[0] == "!flag":
                user = await client.fetch_user(message.content.split()[1])
                await send_captcha(user)
                return



@client.event
async def on_member_join(member):
    watch_list.append({member.name, member.id, member.joined_at}) # Add member to watch list

    # Keep the watch list length smaller than watch_list_length
    if len(watch_list) > watch_list_length:
        watch_list.pop(0)

    with open("blacklist.txt", "r") as f:
        blacklist = f.readlines()
        if member.name in blacklist:
            await send_captcha(member)
            return

    # Logic to determine if user is sus
    
    if len(watch_list) > 1:

        # Check if user joined within 30 seconds of previous user
        if watch_list[-1]["joined_at"] - watch_list[-2]["joined_at"] < datetime.timedelta(seconds=30):
            await send_captcha(member) # Send captcha to user
            # if previous user hasn't been flagged, flag them and send captcha to them too
            if watch_list[-2]["id"] not in captcha_list.keys():
                try:
                    previous_user = await client.fetch_user(watch_list[-2]["id"])
                    await previous_user.remove_roles(discord.utils.get(member.guild.roles, name=verified_role))
                    await send_captcha(previous_user)
                except discord.NotFound:
                    print("Previous user not found")
                except:
                    print("Error trying to flag previous user")
            return
    

    member.add_roles(discord.utils.get(member.guild.roles, name=verified_role)) # Give verified role to user

    # Check if a user is similar to a watch list user (compare similarity in names and discriminators)
    # We can either use predifined username parser or some sklearn algorithm 
    # If yes, send a captcha to the user
    # Send a captcha to the user and quarantine user.

    print(f'{member} has joined the server.')

# Send the captcha to user and returns the answer to the captcha
async def send_captcha(user, tries = max_tries):
    # Remove verified role if user has it
    if verified_role in user.roles:
        await user.remove_roles(discord.utils.get(user.guild.roles, name=verified_role))

    bytes, answer = generate_captcha()
    img_file = discord.File(bytes, filename="captcha.png")
    emoji = discord.utils.get(client.emojis, name='sus')
    embed = discord.Embed(title=f"Oops, are you a robot? {str(emoji)}", description="We've noticied some anomalies with your account. There is no need to worry. Please respond with the text in the captcha to verify your identity and access the Kurius Discord server.", color=0xFF0000)
    embed.set_image(url='attachment://captcha.png')
    captcha_list[user.id] = {answer, tries}
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
    

if __name__ == '__main__':
    client.run(TOKEN)
