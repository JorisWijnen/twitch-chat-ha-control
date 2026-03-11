import logging
import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN
from .twitch import TwitchBot

DOMAIN = "twitch_control"

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config):
    """Set up Twitch Control from YAML (if used)."""
    return True  # We use config flow, so setup from YAML does nothing

async def async_setup_entry(hass, entry):
    """Set up Twitch Control from a config entry."""
    data = entry.data
    
    bot = TwitchBot(
        hass,
        data["twitch_oauth_token"],
        data["twitch_channel"],
        data["client_id"],
        data["client_secret"],
        data["bot_id"]
    )

    # Store the bot instance in hass.data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = bot

    # Register the service for this specific entry
    async def handle_send_message(call):
        msg = call.data.get("message", "Hello from Home Assistant!")
        await bot.send_message(msg)

    hass.services.async_register(DOMAIN, "send_message", handle_send_message)

    # Start the bot as a background task
    entry.async_create_background_task(hass, bot.start(), "twitch-bot-start")

    # Register the send_message service
    async def handle_send_message(call):
        """Send a message to Twitch chat."""
        message = call.data.get("message", "Hello from Home Assistant!")
        await bot.send_message(message)

    hass.services.async_register(DOMAIN, "send_message", handle_send_message)

    async def start_bot():
        """Start the Twitch bot."""
        _LOGGER.error("Starting Bot")
        
        try:
            await bot.start()
            _LOGGER.error("Twitch Control integration initialized")
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout occurred while starting Twitch bot.")
        except Exception as e:
            _LOGGER.error(f"Error starting Twitch bot: {e}")

    hass.loop.create_task(start_bot())  # Ensure bot starts after HA is initialized

    # Listen for the twitch_command event
    async def handle_twitch_command(event):
        """Handle the twitch_command event."""
        message = event.data.get("message")
        if message:
            # Add your automation control logic here
            _LOGGER.error(f"Handling Twitch command: {message}")
            # Example: Turn on a light
            await hass.services.async_call("light", "turn_on", {"entity_id": "light.your_light_entity"})

    hass.bus.async_listen("twitch_command", handle_twitch_command)

    return True

async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    bot = hass.data[DOMAIN].pop(entry.entry_id)
    await bot.close()
    return True
