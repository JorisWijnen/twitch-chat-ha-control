import logging
import twitchio
from .const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from twitchio.ext import commands
from twitchio import eventsub

_LOGGER = logging.getLogger(__name__)

class TwitchBot(commands.AutoBot):
    def __init__(self, hass, client_id, client_secret, bot_id, owner_id):
        self.hass = hass
        # subscribe to eventsub 'chat' of owner_id's twitch channel
        subs = [
        eventsub.ChatMessageSubscription(broadcaster_user_id=owner_id, user_id=bot_id),
        ]
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            bot_id=bot_id,
            owner_id=owner_id,
            subscriptions=subs,
            force_subscribe=True,
            prefix="!",
        )
       
    async def event_ready(self):
        """When the bot is connected and ready."""
        _LOGGER.info(f"Twitch bot connected as {self.nick} to channel {self.channel_name}")

    async def event_message(self, message: twitchio.ChatMessage):
        """Handle incoming messages from the Twitch chat."""
        if message.echo or not message.author:
            return

        if message.content.startswith("!lights"):
            args = message.content.split()
            color = args[1] if len(args) > 1 else "default"
            _LOGGER.info(f"Twitch command received: lights with color {color}")

            # Trigger Home Assistant automation
            await self.hass.services.async_call(
                "automation", "trigger",
                {"entity_id": "automation.twitch_lights", "variables": {"color": color}},
                context=None
            )

    async def send_message(self, message: str):
        """Send a message to the Twitch channel."""
        # Ensure we wait for the channel to be ready/joined
        channel = self.get_channel(self.channel_name)
        if channel:
            await channel.send(message)
        else:
            _LOGGER.error(f"Could not find channel {self.channel_name} to send message.")

    async def close(self):
        """Gracefully shut down the bot."""
        _LOGGER.info("Closing Twitch bot...")
        await super().close()

    @commands.command()
    async def lights(self, message: twitchio.ChatMessage):
        pass

async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the Twitch integration."""
    client_id = config[DOMAIN]["client_id"]
    client_secret = config[DOMAIN]["client_secret"]
    bot_id = config[DOMAIN]["bot_id"]
    owner_id = config[DOMAIN]["owner_id"]
    
    _LOGGER.error("Starting Bot with credentials: ")

    bot = TwitchBot(hass, client_id, client_secret, bot_id, owner_id)
    hass.data[DOMAIN] = bot

    # Listen for Home Assistant stop to gracefully close the bot
    async def on_shutdown(event):
        await bot.close()
    hass.bus.async_listen_once("homeassistant_stop", on_shutdown)

    # Register the service
    async def handle_send_message(call):
        """Handle sending a message to Twitch chat."""
        message = call.data.get("message", "Hello from Home Assistant!")
        await bot.send_message(message)

    hass.services.async_register(DOMAIN, "send_message", handle_send_message)

    # Start the bot in an async task
    try:
        await bot.start()
    except Exception as e:
        _LOGGER.error(f"Failed to start Twitch bot: {e}")
        return False  

    return True