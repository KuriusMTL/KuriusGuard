import discord
from multicolorcaptcha import CaptchaGenerator
from io import BytesIO
from datetime import datetime

TOKEN = ''
CAPCTHA_SIZE_NUM = 2

client = discord.Client(intents=discord.Intents.all())
captcha = CaptchaGenerator(CAPCTHA_SIZE_NUM)

watch_list = []
captcha_list = []

@client.event
async def on_ready():
    print(f'{client.user} is up and running.')

@client.event
async def on_message(message):
    if message.author == client.user: return

    # Check if the previous user joined less than a minute ago
    # If so, add the user to the watch list
    # Send a captcha to the user and quarantine user.

    # Check if a user is similar to a watch list user (compare similarity in names and discriminators)
    # We can either use predifined username parser or some sklearn algorithm 
    # If yes, send a captcha to the user
    # Send a captcha to the user and quarantine user.



@client.event
async def on_member_join(member):
    print(f'{member} has joined the server.')

# Send the captcha to user and returns the answer to the captcha
async def send_captcha(user):
        bytes, answer = generate_captcha()
        img_file = discord.File(bytes, filename="captcha.png")
        emoji = discord.utils.get(client.emojis, name='sus')
        embed = discord.Embed(title=f"Oups. Something is sus {str(emoji)}.", description="Hello, we've noticied some anomalies with your account. There is no need to worry. A simple captcha will help us verify your identity. Please respond with the hidden text inside the following image.", color=0xFF0000)
        embed.set_image(url='attachment://captcha.png')
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